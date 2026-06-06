"""Self-test: verify the skill loads, providers register, payloads build,
config validates, and errors classify. NO network calls.

Run: python tests/test_self.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))  # so `import lib` works

# Use a fake API key for env-var-substituted config tests.
os.environ.setdefault("ARK_API_KEY", "fake-ark-key-for-tests")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key-for-tests")
os.environ.setdefault("ALIYUN_BAILIAN_API_KEY", "fake-bailian-key-for-tests")


def test_imports():
    from lib import base, config as cfg, errors, http_async, http_sync
    from lib import registry, request, response, validators
    from lib import providers  # triggers registration
    print("PASS: all lib modules import")
    return cfg, base, errors, registry


def test_providers_registered(registry):
    expected = {"volcengine", "openai-compatible", "aliyun-bailian"}
    actual = set(registry.PROVIDERS)
    if not expected.issubset(actual):
        raise AssertionError(f"missing providers: {expected - actual}")
    print(f"PASS: {len(actual)} providers registered: {sorted(actual)}")


def test_mask_key(base):
    assert base.mask_key("abcdefghijklmnop") == "abcd***mnop"
    assert base.mask_key("short") == "***"
    assert base.mask_key(None) == "<unset>"
    print("PASS: mask_key works as expected")


def test_error_classification(errors):
    e1 = errors.classify("InvalidParameter", "bad", http_status=400)
    assert isinstance(e1, errors.InvalidParameterError)
    e2 = errors.classify("QuotaExceeded", "no credits")
    assert isinstance(e2, errors.QuotaExceededError)
    e3 = errors.classify("SensitiveContentBlocked", "blocked")
    assert isinstance(e3, errors.SensitiveContentError)
    e4 = errors.classify("Unknown", "server error", http_status=500)
    assert isinstance(e4, errors.InternalServerError)
    print("PASS: error classification routes prefixes correctly")


def test_config_loads(base, cfg):
    """Load the live config.yaml (with env-var substitution) and validate."""
    config_path = SKILL_DIR / "config.yaml"
    if not config_path.is_file():
        print(f"SKIP: {config_path} not found")
        return
    config = cfg.load_config(config_path)
    assert "volcengine" in config.providers
    assert config.default_provider in config.providers
    for name, spec in config.providers.items():
        assert spec.api_key, f"{name} missing api_key after env expansion"
        assert spec.base_url, f"{name} missing base_url"
    # Verify masking
    for name, spec in config.providers.items():
        masked = base.mask_key(spec.api_key)
        assert "fake-ark-key" not in masked or "***" in masked, \
            f"key not masked: {masked}"
    print(f"PASS: config.yaml loaded with {len(config.providers)} providers, keys masked")


def test_volcengine_payload(registry, cfg):
    """Build a payload and inspect it without sending."""
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "volcengine")
    prov = registry.instantiate(spec.type, spec)
    payload = prov.build_payload(
        "test cat", size="2K", sequential=True, max_images=4,
        optimize_mode="standard", web_search=True,
    )
    assert payload["model"].startswith("doubao-seedream")
    assert payload["size"] == "2K"
    assert payload["sequential_image_generation"] == "auto"
    assert payload["sequential_image_generation_options"]["max_images"] == 4
    assert payload["optimize_prompt_options"]["mode"] == "standard"
    assert payload["tools"] == [{"type": "web_search"}]
    print(f"PASS: volcengine payload has {len(payload)} keys, schema matches API doc")


def test_openai_payload(registry, cfg):
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "openai")
    prov = registry.instantiate(spec.type, spec)
    payload = prov.build_payload("test", size="1024x1024")
    assert payload["model"] == "gpt-image-1"
    assert payload["size"] == "1024x1024"
    print("PASS: openai payload builds")


def test_multi_image_wraps_single(registry, cfg):
    """volcengine with multi_image=True wraps a single image in a list."""
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "volcengine")
    # Override multi_image for this test
    spec.multi_image = True
    prov = registry.instantiate(spec.type, spec)
    payload = prov.build_payload("test", image="https://example.com/cat.png", size="2K")
    assert isinstance(payload["image"], list), \
        f"expected list, got {type(payload['image'])}"
    assert len(payload["image"]) == 1
    print("PASS: multi_image=True wraps single image in a list")


def test_multi_image_passes_list(registry, cfg):
    """volcengine without multi_image passes a list through unchanged."""
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "volcengine")
    prov = registry.instantiate(spec.type, spec)
    payload = prov.build_payload(
        "test",
        image=["https://example.com/a.png", "https://example.com/b.png"],
        size="2K",
    )
    assert isinstance(payload["image"], list), \
        f"expected list, got {type(payload['image'])}"
    assert len(payload["image"]) == 2
    print("PASS: multi-image list passes through")


def test_image_field_override(registry, cfg):
    """image_field='image_urls' changes the wire key."""
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "volcengine")
    spec.image_field = "image_urls"
    prov = registry.instantiate(spec.type, spec)
    payload = prov.build_payload("test", image="https://example.com/cat.png", size="2K")
    assert "image_urls" in payload, f"expected 'image_urls' key, got {list(payload)}"
    assert "image" not in payload, "plain 'image' key should not exist"
    print("PASS: image_field override works")


def test_validate_size_rejects_small(registry, cfg):
    """volcengine 5.0-lite requires >= 3.6M pixels."""
    config_path = SKILL_DIR / "config.yaml"
    config = cfg.load_config(config_path)
    spec = cfg.get_provider(config, "volcengine")
    prov = registry.instantiate(spec.type, spec)
    try:
        prov.validate_size("1024x1024")  # 1M pixels, too small
    except Exception as e:
        if "out of range" in str(e):
            print("PASS: small size correctly rejected client-side")
            return
        raise
    raise AssertionError("expected validation error for 1024x1024")


def test_validate_config_cli():
    """Run the validate_config.py script and check exit code."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "validate_config.py")],
        capture_output=True, text=True, timeout=30,
    )
    print(f"  validate_config.py exit: {result.returncode}")
    print(f"  stdout: {result.stdout.strip()[:200]}")
    if result.stderr:
        print(f"  stderr: {result.stderr.strip()[:200]}")
    if result.returncode != 0:
        raise AssertionError(f"validate_config.py failed: {result.stdout}\n{result.stderr}")
    if "OK" not in result.stdout:
        raise AssertionError("expected 'OK' in stdout")
    print("PASS: validate_config.py exits 0 with OK")


def test_no_full_key_in_masking(base):
    """Ensure that even when the key contains a recognizable prefix, the
    masked form does not leak the full key."""
    key = "ark-1234567890abcdef"
    masked = base.mask_key(key)
    assert key not in masked, f"full key leaked: {masked!r}"
    assert "***" in masked
    print(f"PASS: '{key}' -> '{masked}' (no leak)")


def test_auto_copy_creates_config(cfg, base):
    """When config.yaml is missing but config.example.yaml exists, auto-copy + hint."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        example = Path(tmpdir) / "config.example.yaml"
        example.write_text("""default_provider: test123
providers:
  test123:
    type: openai-compatible
    base_url: https://api.example.com/v1
    api_key: ${TEST_API_KEY}
    model: test-model
""", encoding="utf-8")
        config_path = Path(tmpdir) / "config.yaml"
        try:
            cfg.load_config(config_path)
        except base.GenerateError as e:
            msg = str(e)
            assert "Created" in msg, f"expected 'Created', got: {msg}"
            assert "Edit this file" in msg, f"expected edit hint, got: {msg}"
            assert "fill in your API keys" in msg, f"expected key hint, got: {msg}"
            # Verify the file was actually copied
            assert config_path.is_file(), "config.yaml should exist after auto-copy"
            assert config_path.read_text() == example.read_text(), \
                "copied file should match template"
            print("PASS: auto-copy creates config from template with helpful message")
        else:
            raise AssertionError("expected GenerateError from auto-copy")


def test_auto_copy_missing_template(cfg, base):
    """When neither config.yaml nor config.example.yaml exist, clear error."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        try:
            cfg.load_config(config_path)
        except base.GenerateError as e:
            msg = str(e)
            assert "also missing" in msg, f"expected 'also missing', got: {msg}"
            assert "config.example.yaml" in msg, \
                f"expected mention of template, got: {msg}"
            print("PASS: missing-template error is clear and actionable")
        else:
            raise AssertionError("expected GenerateError when both files missing")


def main() -> int:
    print(f"Skill dir: {SKILL_DIR}")
    print()
    cfg, base, errors, registry = test_imports()
    test_providers_registered(registry)
    test_mask_key(base)
    test_error_classification(errors)
    test_config_loads(base, cfg)
    test_volcengine_payload(registry, cfg)
    test_openai_payload(registry, cfg)
    test_multi_image_wraps_single(registry, cfg)
    test_multi_image_passes_list(registry, cfg)
    test_image_field_override(registry, cfg)
    test_validate_size_rejects_small(registry, cfg)
    test_validate_config_cli()
    test_no_full_key_in_masking(base)
    test_auto_copy_creates_config(cfg, base)
    test_auto_copy_missing_template(cfg, base)
    print()
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
