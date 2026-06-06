"""SSE (Server-Sent Events) streaming parser for image generation.

Yields raw event dicts as they arrive, line by line. Requires aiohttp.
The async HTTP module (http_async.py) wraps this for `stream=True` requests.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict

try:
    import aiohttp
except ImportError as _e:  # pragma: no cover
    aiohttp = None  # type: ignore
    _IMPORT_ERR = _e


class StreamingUnavailable(ImportError):
    """Raised when streaming is requested but aiohttp is not installed."""


async def _ensure_aiohttp() -> None:
    if aiohttp is None:
        raise StreamingUnavailable(
            "streaming requires aiohttp. Install with: pip install aiohttp"
        ) from _IMPORT_ERR


async def post_sse(
    url: str,
    payload: Dict[str, Any],
    api_key: str,
    *,
    timeout: float = 120.0,
) -> AsyncIterator[Dict[str, Any]]:
    """POST JSON, expect SSE stream, yield each `data:` line as a parsed dict.

    Per the OpenAI / ARK streaming protocol, each event line is `data: {...}`.
    The stream ends with `data: [DONE]`.
    """
    await _ensure_aiohttp()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise RuntimeError(f"HTTP {resp.status}: {body}")
            async for raw in resp.content:
                line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    return
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
