"""Normalize the `image` parameter to whatever the provider accepts.

The volcengine ARK spec says `image` is `string | array`. Each entry can be:
  - A public URL (http/https)
  - A data URI:    data:image/<fmt>;base64,<...>
  - A local file:  /path/to/x.png  -> we read it, base64-encode, build a data URI

Up to 14 reference images for volcengine 5.0-lite. Most other providers accept
fewer; we cap at 14 and let the server enforce its own policy.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Iterable, List, Union

from .errors import InvalidParameterError

_MAX_IMAGES = 14
_SUPPORTED_FORMATS = {
    "jpeg", "jpg", "png", "webp", "bmp", "tiff", "tif", "gif", "heic", "heif",
}
_MAX_BYTES = 30 * 1024 * 1024  # 30 MB


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _is_data_uri(s: str) -> bool:
    return s.startswith("data:")


def _detect_format_from_data_uri(uri: str) -> str:
    try:
        head = uri.split(",", 1)[0]
        mime = head.split(":", 1)[1].split(";", 1)[0]
        return mime.split("/", 1)[1].lower()
    except Exception as e:
        raise InvalidParameterError(f"malformed data URI: {e}") from e


def _encode_local(path: Union[str, Path]) -> str:
    p = Path(path)
    if not p.is_file():
        raise InvalidParameterError(f"image file not found: {p}")
    if p.stat().st_size > _MAX_BYTES:
        raise InvalidParameterError(
            f"image too large: {p} = {p.stat().st_size} bytes (max {_MAX_BYTES})"
        )
    ext = p.suffix.lstrip(".").lower() or "png"
    if ext == "jpg":
        ext = "jpeg"
    if ext not in _SUPPORTED_FORMATS:
        raise InvalidParameterError(
            f"unsupported image format {ext!r}; "
            f"allowed: {sorted(_SUPPORTED_FORMATS)}"
        )
    mime, _ = mimetypes.guess_type(str(p))
    if not mime:
        mime = f"image/{ext}"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def normalize_image(image: Union[str, Path, Iterable[Union[str, Path]], None]) -> Union[str, List[str], None]:
    """Convert the user-supplied `image` to one of:
      - None  (when input is None / empty)
      - str   (single entry)
      - list[str]  (multiple entries)
    """
    if image is None:
        return None
    if isinstance(image, (str, Path)):
        items: List[Union[str, Path]] = [image]
    else:
        items = list(image)
        if not items:
            return None

    if len(items) > _MAX_IMAGES:
        raise InvalidParameterError(
            f"too many reference images: {len(items)} (max {_MAX_IMAGES})"
        )

    out: List[str] = []
    for it in items:
        if isinstance(it, Path) or (
            isinstance(it, str) and not _is_url(it) and not _is_data_uri(it)
        ):
            s = str(it)
            if os.path.exists(s):
                out.append(_encode_local(s))
            else:
                # Not a file we can see; pass through and let the server decide.
                out.append(s)
        elif _is_url(it):
            out.append(it)
        elif _is_data_uri(it):
            fmt = _detect_format_from_data_uri(it)
            if fmt not in _SUPPORTED_FORMATS:
                raise InvalidParameterError(
                    f"unsupported image format in data URI: {fmt!r}"
                )
            out.append(it)
        else:  # pragma: no cover
            raise InvalidParameterError(f"unsupported image input: {it!r}")

    return out[0] if len(out) == 1 else out
