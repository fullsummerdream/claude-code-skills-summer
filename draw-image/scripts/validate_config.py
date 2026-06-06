"""Validate config.yaml: check syntax, env-var resolution, and provider
import. Exits 0 on success, non-zero with a clear error otherwise.

Always masks API keys in its output.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = SKILL_DIR / "lib"
CONFIG_PATH = SKILL_DIR / "config.yaml"
sys.path.insert(0, str(SKILL_DIR))  # so `import lib` works


def main() -> int:
    # Ensure dependencies are present (friendly errors, not full tracebacks)
    try:
        import pydantic  # noqa
    except ImportError:
        print("Missing dependency: pydantic. Run: pip install pydantic>=2.0",
              file=sys.stderr)
        return 10
    try:
        import yaml  # noqa
    except ImportError:
        print("Missing dependency: pyyaml. Run: pip install pyyaml>=6.0",
              file=sys.stderr)
        return 10

    from lib import config as cfg
    from lib import base
    from lib import registry
    # Trigger built-in provider registration
    import lib.providers.volcengine  # noqa: F401
    import lib.providers.openai_compatible  # noqa: F401
    import lib.providers.aliyun_bailian  # noqa: F401

    if not CONFIG_PATH.is_file():
        print(f"FAIL: config not found: {CONFIG_PATH}", file=sys.stderr)
        print("  Copy config.example.yaml to config.yaml and fill in the keys.",
              file=sys.stderr)
        return 1

    print(f"Loading {CONFIG_PATH}...")
    try:
        config = cfg.load_config(CONFIG_PATH)
    except base.GenerateError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"  default_provider: {config.default_provider}")
    print(f"  providers: {len(config.providers)}")
    for name, spec in config.providers.items():
        masked = base.mask_key(spec.api_key)
        print(f"    - {name}: type={spec.type}, model={spec.model}, api_key={masked}")

    # Dry-run: build a request for each provider without sending
    print()
    print("Dry-run build_payload for each provider:")
    failures = 0
    for name, spec in config.providers.items():
        try:
            prov = registry.instantiate(spec.type, spec)
            payload = prov.build_payload("__validate_only__", size=spec.default_size)
            print(f"  {name}: OK ({len(payload)} keys)")
        except Exception as e:
            print(f"  {name}: FAIL [{type(e).__name__}] {e}")
            failures += 1

    print()
    if failures:
        print(f"FAIL: {failures} provider(s) failed dry-run.")
        return 1
    print("OK: config is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
