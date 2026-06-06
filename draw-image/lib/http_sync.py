"""Synchronous HTTP client for image generation. Stdlib urllib only.

Used by every provider's sync `generate()` path. Retries 2x on transient errors.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from .errors import GenerateError, classify

_MAX_RETRIES = 2
_DEFAULT_TIMEOUT = 120.0


def post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    api_key: str,
    auth_header: str = "Authorization",
    timeout: float = _DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """POST JSON, return parsed dict. Retries on 5xx/429/URLError only."""
    body = json.dumps(payload).encode("utf-8")
    last_err: GenerateError = None  # type: ignore
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return _one_request(url, body, api_key=api_key,
                                auth_header=auth_header, timeout=timeout)
        except GenerateError as e:
            last_err = e
            # Don't retry on client errors (4xx, except 429)
            if e.http_status and 400 <= e.http_status < 500 and e.http_status != 429:
                raise
            if attempt < _MAX_RETRIES:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # pragma: no cover


def _one_request(
    url: str,
    body: bytes,
    *,
    api_key: str,
    auth_header: str,
    timeout: float,
) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            auth_header: f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(raw)
            code = err.get("error", {}).get("code", "")
            msg = err.get("error", {}).get("message", raw)
        except json.JSONDecodeError:
            code, msg = "", raw
        raise classify(code or f"HTTP{e.code}", msg, http_status=e.code) from e
    except urllib.error.URLError as e:
        raise classify("NetworkError", f"network error: {e.reason}") from e


def download_to(url: str, dest_path, *, timeout: float = 60.0) -> None:
    """Download a remote image URL to a local path. Used by every provider."""
    with urllib.request.urlopen(url, timeout=timeout) as resp, \
            open(dest_path, "wb") as f:
        f.write(resp.read())
