"""Asynchronous HTTP client for image generation. Requires aiohttp.

Used by every provider's async `stream()` path. The `run_async` helper is the
agent-safe entry point: it works whether or not the caller is already inside
an event loop (Claude Code agents sometimes are).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, AsyncIterator, Dict

from .errors import classify
from .streaming import post_sse


# ---- run_async: handle the "we're already inside a loop" case ----------------

def run_async(coro_factory) -> Any:
    """Run an awaitable from sync code, safely.

    - If no event loop is running: use asyncio.run().
    - If one IS running (agent, Jupyter, etc.): run the coroutine in a
      separate thread with its own loop, then return the result.

    This is what the CLI calls when `--stream` is used, even though the
    CLI itself is synchronous. It avoids the "asyncio.run() cannot be called
    from a running loop" RuntimeError.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop: clean asyncio.run
        return asyncio.run(coro_factory())

    # Loop is already running: spin up a new thread + loop for this coroutine.
    # (Installing nest_asyncio would also work but adds a dependency.)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(coro_factory())).result()


# ---- async_post / async_stream -----------------------------------------------

async def async_post(
    url: str,
    payload: Dict[str, Any],
    *,
    api_key: str,
    auth_header: str = "Authorization",
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """POST JSON asynchronously and return parsed dict."""
    import aiohttp  # lazy import: aiohttp is optional
    headers = {
        "Content-Type": "application/json",
        auth_header: f"Bearer {api_key}",
    }
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            raw = await resp.text()
            if resp.status >= 400:
                try:
                    err = json.loads(raw)
                    code = err.get("error", {}).get("code", "")
                    msg = err.get("error", {}).get("message", raw)
                except Exception:
                    code, msg = "", raw
                raise classify(code or f"HTTP{resp.status}", msg, http_status=resp.status)
            return json.loads(raw)


async def async_stream(
    url: str,
    payload: Dict[str, Any],
    *,
    api_key: str,
    auth_header: str = "Authorization",
    timeout: float = 120.0,
) -> AsyncIterator[Dict[str, Any]]:
    """Stream SSE events asynchronously. Delegates to streaming.post_sse."""
    async for event in post_sse(url, payload, api_key, timeout=timeout):
        yield event
