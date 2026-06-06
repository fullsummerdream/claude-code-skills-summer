"""Parameter validators for image generation requests."""

from __future__ import annotations

import re
from typing import Optional

from .errors import InvalidParameterError


# ---- prompt -----------------------------------------------------------------

# volcengine doc says: "<= 300 hanzi / 600 words".
_HANZI = re.compile(r"[一-鿿㐀-䶿＀-￯]")


def _count_units(text: str) -> tuple[int, int]:
    hanzi = len(_HANZI.findall(text))
    tokens = text.split()
    words = sum(1 for t in tokens if any(c.isalpha() and c.isascii() for c in t))
    return hanzi, words


def validate_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        raise InvalidParameterError("prompt must not be empty")
    hanzi, words = _count_units(prompt)
    if hanzi > 300 or words > 600:
        raise InvalidParameterError(
            f"prompt too long: {hanzi} hanzi / {words} words; "
            f"recommended <= 300 hanzi / 600 words"
        )
    return prompt.strip()


# ---- size -------------------------------------------------------------------

_RESOLUTION_PRESETS = {"1K", "2K", "3K", "4K"}

# Per-model pixel and aspect-ratio ranges. volcengine 5.0-lite is the strictest baseline.
_MODEL_RANGES = {
    "doubao-seedream-5-0-260128": {
        "pixels": (3_686_400, 16_777_216),
        "ratio": (1 / 16, 16),
    },
    "doubao-seedream-4-5": {
        "pixels": (3_686_400, 16_777_216),
        "ratio": (1 / 16, 16),
    },
    "doubao-seedream-4-0": {
        "pixels": (921_600, 16_777_216),
        "ratio": (1 / 16, 16),
    },
}

_SIZE_PATTERN = re.compile(r"^(\d+)x(\d+)$")


def _default_range_for(model: str) -> dict:
    for prefix, rng in _MODEL_RANGES.items():
        if model.startswith(prefix):
            return rng
    return _MODEL_RANGES["doubao-seedream-5-0-260128"]


def validate_size(size: Optional[str], *, model: str) -> str:
    """Accept '<W>x<H>' or a resolution preset like '2K'/'3K'/'4K'."""
    if size is None:
        return "2048x2048"
    s = str(size).strip()
    if s in _RESOLUTION_PRESETS:
        return s
    m = _SIZE_PATTERN.match(s)
    if not m:
        raise InvalidParameterError(
            f"invalid size {size!r}: expected 'WxH' (e.g. 2048x2048) or 2K/3K/4K"
        )
    w, h = int(m.group(1)), int(m.group(2))
    if w <= 0 or h <= 0:
        raise InvalidParameterError(f"size must be positive, got {w}x{h}")
    pixels = w * h
    rng = _default_range_for(model)
    if not (rng["pixels"][0] <= pixels <= rng["pixels"][1]):
        raise InvalidParameterError(
            f"size {w}x{h} = {pixels} px out of range "
            f"[{rng['pixels'][0]}, {rng['pixels'][1]}] for model {model}"
        )
    ratio = w / h
    if not (rng["ratio"][0] <= ratio <= rng["ratio"][1]):
        raise InvalidParameterError(
            f"aspect ratio {ratio:.3f} out of range "
            f"[{rng['ratio'][0]:.4f}, {rng['ratio'][1]}] for model {model}"
        )
    return s
