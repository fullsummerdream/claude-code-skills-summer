"""auto_add_provider.py — semi-automated new provider from a PDF.

Reads a provider's API PDF, extracts common structural markers, and emits
a YAML block (with TODO markers) the user (or agent) can complete and
paste into config.yaml.

Usage:
  python scripts/auto_add_provider.py path/to/provider.pdf --provider-name foo
  python scripts/auto_add_provider.py path/to/provider.pdf --provider-name foo --apply

The script NEVER silently overwrites config.yaml. With --apply, it requires
--yes to confirm.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="auto_add_provider",
        description="Generate a draft YAML block for a new image provider from a PDF doc.",
    )
    parser.add_argument("pdf", help="Path to the provider's API PDF")
    parser.add_argument("--provider-name", required=True,
                        help="Short name to use as the YAML key (e.g. 'replicate')")
    parser.add_argument(
        "--type", default="openai-compatible",
        help="Provider type. Default 'openai-compatible' (most common shape).",
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write the draft to config.yaml (requires --yes)")
    parser.add_argument("--yes", action="store_true",
                        help="Confirm the --apply write")
    args = parser.parse_args()

    text = _extract_pdf_text(args.pdf)
    if text is None:
        print("Missing dependency: pypdf. Install with: pip install pypdf",
              file=sys.stderr)
        return 10

    block = _build_yaml_block(args.provider_name, args.type, text)
    print(block)

    if args.apply:
        if not args.yes:
            print("Refusing to write without --yes. Re-run with --apply --yes to confirm.",
                  file=sys.stderr)
            return 1
        config_path = SKILL_DIR / "config.yaml"
        if not config_path.is_file():
            print(f"FAIL: {config_path} not found. Run the skill at least once first.",
                  file=sys.stderr)
            return 1
        existing = config_path.read_text(encoding="utf-8")
        if re.search(rf"^\s*{re.escape(args.provider_name)}:\s*$", existing, re.MULTILINE):
            print(f"FAIL: provider {args.provider_name!r} already exists in config.yaml. "
                  f"Refusing to overwrite.", file=sys.stderr)
            return 1
        config_path.write_text(existing.rstrip() + "\n\n" + block + "\n",
                               encoding="utf-8")
        print(f"\nAppended to {config_path}. Review and fill in TODOs.",
              file=sys.stderr)
    return 0


def _extract_pdf_text(pdf_path: str) -> str | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    reader = PdfReader(pdf_path)
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _build_yaml_block(name: str, ptype: str, text: str) -> str:
    """Heuristic extraction. The agent (or human) is expected to fill TODOs."""

    # --- URL: prefer API-looking URLs over docs links ---
    all_urls = re.findall(r"https?://[^\s)<>\"']+", text)
    api_urls = [u for u in all_urls if re.search(r"(api|/v[123]/|/images/)", u)]
    base_url = (api_urls or all_urls or [None])[0]
    if base_url:
        # Strip trailing path segments that look like endpoints, keep the root
        base_url = re.sub(r"/(v\d+/)?images/generations.*", "", base_url)
        base_url = base_url.rstrip("/")

    # --- Auth scheme ---
    auth_lower = text.lower()
    if "x-api-key" in auth_lower or "x-api-key" in text:
        auth_header = "x-api-key"
        auth_scheme = "API key header"
    elif "accesskey" in auth_lower or "access key" in auth_lower:
        auth_header = "Authorization"
        auth_scheme = "AccessKey (may need HMAC signing — check PDF)"
    elif "api-key" in auth_lower:
        auth_header = "x-api-key"
        auth_scheme = "API key header"
    elif "bearer" in auth_lower:
        auth_header = "Authorization"
        auth_scheme = "Bearer token"
    elif "authorization" in auth_lower:
        auth_header = "Authorization"
        auth_scheme = "Bearer (verify in PDF)"
    else:
        auth_header = "TODO_AUTH_HEADER_NAME"
        auth_scheme = "TODO — check PDF for auth method"

    # --- Model ID: look for quoted strings after "model", or endpoint-id patterns ---
    model_matches = re.findall(
        r"""["']model["']\s*:\s*["']([^"']+)["']""", text
    )
    model = model_matches[0] if model_matches else None
    if not model:
        # Try endpoint-id pattern: ep-XXXX, or model names like xxx-xxx-xxx
        ep = re.findall(r"\b(ep-[a-zA-Z0-9_-]+)", text)
        if ep:
            model = ep[0]
    if not model:
        # Try path segments that look like model IDs
        path_model = re.findall(r"/(models|endpoints)/([a-zA-Z0-9_-]+)", text)
        if path_model:
            model = path_model[0][1]

    # --- Size constraints ---
    size_notes = []
    if re.search(r"(pixels?|resolution)", auth_lower):
        px_min = re.findall(r"(?:at least|minimum|min|≥|>=)\s*(\d[\d,]*)\s*(?:pixels?|px)?", auth_lower)
        px_max = re.findall(r"(?:at most|maximum|max|≤|<=|up to)\s*(\d[\d,]*)\s*(?:pixels?|px)?", auth_lower)
        if px_min:
            size_notes.append(f"min {px_min[0]} px")
        if px_max:
            size_notes.append(f"max {px_max[0]} px")
    if re.search(r"aspect ratio", auth_lower):
        ratios = re.findall(r"(\d+)\s*:\s*(\d+)", auth_lower)
        if ratios:
            size_notes.append(f"aspect ratio around {ratios[0][0]}:{ratios[0][1]}")
    default_size = "TODO_DEFAULT_SIZE"
    if "2048" in text:
        default_size = "2048x2048"
    elif "1024" in text:
        default_size = "1024x1024"

    # --- Multi-image support ---
    multi_image_hint = ""
    if re.search(r"(max_images|max_ref|reference_images|multiple.*image|multiple.*reference)", auth_lower):
        max_imgs = re.findall(r"(?:up to|max(?:imum)?|at most)\s*(\d+)\s*(?:reference)?\s*images?", auth_lower)
        if max_imgs:
            multi_image_hint = f"  # up to {max_imgs[0]} reference images"
        else:
            multi_image_hint = "  # supports multiple reference images — check PDF for limit"

    # --- Streaming ---
    streaming_hint = ""
    if re.search(r"(stream|SSE|server-sent|server.sent|text/event-stream)", text):
        streaming_hint = "  # streaming (SSE) appears to be supported — verify endpoint in PDF"

    # --- Response format ---
    if re.search(r"b64_json|base64", auth_lower):
        response_format = "url"
    else:
        response_format = "url"

    # --- Output format ---
    output_hint = ""
    if re.search(r"\b(png|jpe?g|webp)\b", auth_lower):
        output_hint = "  # check PDF for supported output formats (png/jpeg/webp)"

    # --- Build YAML ---
    lines = []
    lines.append("# WARNING: best-effort extraction from PDF. You MUST verify every field.")
    lines.append(f"# Auth: {auth_scheme}")
    if size_notes:
        lines.append(f"# Size constraints detected: {', '.join(size_notes)}")
    lines.append(f"# Base URL guess: {base_url or 'NOT FOUND — check PDF section on endpoints'}")
    lines.append("")
    lines.append(f"  {name}:")
    lines.append(f"    type: {ptype}")
    lines.append(f"    base_url: {base_url or 'TODO_BASE_URL  # find the API root URL in the PDF'}")
    lines.append(f"    api_key: ${{{name.upper().replace('-', '_')}_API_KEY}}    # <-- REPLACE HERE")
    lines.append(f"    model: {model or 'TODO_MODEL_ID  # find in PDF (endpoint id or model name)'}")
    lines.append(f"    default_size: {default_size}")
    if multi_image_hint:
        lines.append(f"    # multi_image: true{multi_image_hint}")
    if streaming_hint:
        lines.append(streaming_hint)
    if output_hint:
        lines.append(output_hint)
    lines.append(f"    # auth_header_name: {auth_header}  # verify in PDF")
    lines.append(f"    # response_format: {response_format}")
    lines.append(f"    # request_fields: {{}}     # map field names if provider uses non-OpenAI names")
    lines.append(f"    # extra_params: {{}}        # pin any fixed params the API requires")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
