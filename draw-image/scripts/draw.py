"""draw-image CLI: main entry point.

Usage:
  python scripts/draw.py "a cat in a window"
  python scripts/draw.py --provider openai "logo design"
  python scripts/draw.py --stream "four fruit icons"
  python scripts/draw.py --validate-config
  python scripts/draw.py --json "a cat" | jq

The script auto-locates the skill directory via __file__, so you can run it
from any working directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json as jsonlib
import os
import sys
from pathlib import Path

# Locate skill dir regardless of CWD.
SKILL_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = SKILL_DIR / "lib"
CONFIG_PATH = SKILL_DIR / "config.yaml"
sys.path.insert(0, str(SKILL_DIR))  # so `import lib` works


def _import_lib():
    """Import the library, printing friendly messages on ImportError."""
    try:
        import pydantic  # noqa
    except ImportError:
        print(
            "Missing dependency: pydantic.\n"
            "Install with: pip install pydantic>=2.0",
            file=sys.stderr,
        )
        sys.exit(10)
    try:
        import yaml  # noqa
    except ImportError:
        print(
            "Missing dependency: pyyaml.\n"
            "Install with: pip install pyyaml>=6.0",
            file=sys.stderr,
        )
        sys.exit(10)
    from lib import config as cfg
    from lib import registry
    from lib import base
    # Trigger built-in provider registration
    from lib.providers import volcengine  # noqa: F401
    from lib.providers import openai_compatible  # noqa: F401
    from lib.providers import aliyun_bailian  # noqa: F401
    return cfg, registry, base


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="draw",
        description="Generate images using a configured AI provider.",
    )
    parser.add_argument("prompt", nargs="?", help="Image description (text prompt)")
    parser.add_argument(
        "--provider", default=None,
        help="Provider name (defaults to config.yaml's default_provider)",
    )
    parser.add_argument(
        "--size", default=None,
        help="Output size: 'WxH' (e.g. 2048x2048) or preset (2K/3K/4K)",
    )
    parser.add_argument("--image", default=None, help="Reference image (path/URL/data URI)")
    parser.add_argument(
        "--images", nargs="*", default=None,
        help="Multiple reference images. Overrides --image if both are given.",
    )
    parser.add_argument(
        "--n", type=int, default=None,
        help="Number of images (provider-specific; volcengine uses --sequential + --max-images)",
    )
    parser.add_argument("--sequential", action="store_true",
                        help="Generate a group of related images (volcengine only)")
    parser.add_argument("--max-images", type=int, default=None,
                        help="Max images in a group (with --sequential)")
    parser.add_argument("--no-watermark", action="store_true", help="Disable watermark")
    parser.add_argument("--stream", action="store_true",
                        help="Stream images as they generate (requires aiohttp)")
    parser.add_argument("--save-dir", default=None, help="Override save directory")
    parser.add_argument("--response-format", default="url", choices=["url", "b64_json"])
    parser.add_argument("--output-format", default=None, choices=["jpeg", "png"])
    parser.add_argument("--validate-config", action="store_true",
                        help="Only validate config.yaml; don't draw anything")
    parser.add_argument("--json", action="store_true",
                        help="Output a JSON line with paths and usage instead of plain text")
    args = parser.parse_args()

    if args.validate_config:
        return _run_validate()

    if not args.prompt:
        parser.error("prompt is required (unless --validate-config)")

    return _run_generate(args)


def _run_validate() -> int:
    """Run the config validator script and return its exit code."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "validate_config.py")],
    )
    return result.returncode


def _run_generate(args) -> int:
    cfg, registry, base = _import_lib()
    try:
        config = cfg.load_config(CONFIG_PATH)
    except base.GenerateError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    spec = cfg.get_provider(config, args.provider)
    provider = registry.instantiate(spec.type, spec)

    # Apply --save-dir override
    if args.save_dir:
        spec.save_dir = Path(os.path.expanduser(args.save_dir)).resolve()

    # Merge --image / --images into a single value
    image = args.image
    if args.images:
        image = list(args.images)  # list of str

    kwargs = {
        "size": args.size,
        "image": image,
        "response_format": args.response_format,
        "watermark": not args.no_watermark,
        "sequential": args.sequential,
        "max_images": args.max_images,
        "n": args.n,
    }
    if args.output_format:
        kwargs["output_format"] = args.output_format

    try:
        if args.stream:
            return _run_stream(provider, args.prompt, kwargs, args.json)
        return _run_sync(provider, args.prompt, kwargs, args.json)
    except base.GenerateError as e:
        # Key is always masked. e.message never contains the full key.
        print(f"Failed [{type(e).__name__}]: {e}", file=sys.stderr)
        if e.http_status:
            print(f"  HTTP status: {e.http_status}", file=sys.stderr)
        if e.code:
            print(f"  Error code: {e.code}", file=sys.stderr)
        return 2


def _run_sync(provider, prompt, kwargs, as_json) -> int:
    resp = provider.generate(prompt, **kwargs)
    if as_json:
        out = {
            "model": resp.model,
            "created": resp.created,
            "paths": [str(p) for p in resp.paths],
            "usage": {
                "generated_images": resp.usage.generated_images,
                "output_tokens": resp.usage.output_tokens,
                "total_tokens": resp.usage.total_tokens,
                "web_search_calls": resp.usage.web_search_calls,
            },
        }
        print(jsonlib.dumps(out, ensure_ascii=False, indent=2))
    else:
        for p in resp.paths:
            print(p)
    if not resp.paths:
        return 3
    return 0


def _run_stream(provider, prompt, kwargs, as_json) -> int:
    try:
        from lib.http_async import run_async
    except ImportError as e:
        print(f"Streaming unavailable: {e}", file=sys.stderr)
        print("Install with: pip install aiohttp", file=sys.stderr)
        return 4

    # Stream mode is async, but the CLI itself is sync: use run_async to
    # handle the "we're already in a loop" case (Claude Code agent etc).
    async def _drive():
        paths = []
        async for img in provider.stream(prompt, **kwargs):
            paths.append(str(img.path))
            if not as_json:
                print(img.path)
        return paths

    paths = run_async(_drive)
    if as_json:
        print(jsonlib.dumps({"paths": paths}, ensure_ascii=False, indent=2))
    if not paths:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
