"""Provider abstract base class + the generic OpenAI-compatible implementation.

`Provider` is the single contract every backend must satisfy. Three built-in
providers (volcengine, openai-compatible, aliyun-bailian) live in
`lib/providers/`. YAML-only providers that don't match a built-in get wrapped
in `GenericOpenAICompatibleProvider` at runtime.
"""

from __future__ import annotations

import base64
import os
import random
import string
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from . import http_sync
from .errors import GenerateError
from .image_input import normalize_image
from .response import GenerateResponse, ImageResult, ToolCall, Usage
from .validators import validate_prompt, validate_size


# Key-masking utility. Used everywhere we might log/print an api key.
def mask_key(k: Optional[str]) -> str:
    if not k:
        return "<unset>"
    if len(k) <= 8:
        return "***"
    return f"{k[:4]}***{k[-4:]}"


class Provider(ABC):
    """Abstract base class. Subclasses register themselves via registry.register()."""

    name: str = ""  # set by subclass

    def __init__(self, config):
        self.config = config  # ProviderConfig (defined in config.py)

    # ---- the three hooks every provider must implement --------------------

    @abstractmethod
    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Translate the common request shape into this provider's wire format."""

    @abstractmethod
    def parse_response(self, data: Dict[str, Any]) -> GenerateResponse:
        """Translate this provider's JSON response into a GenerateResponse."""

    @abstractmethod
    def validate_size(self, size: Optional[str]) -> str:
        """Provider-specific size validation. Default delegates to validators.py."""

    # ---- defaults (overridable) -------------------------------------------

    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/images/generations"

    def auth_headers(self) -> Dict[str, str]:
        return {self.config.auth_header_name: f"Bearer {self.config.api_key}"}

    # ---- shared I/O glue --------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> GenerateResponse:
        """Sync generation. Override `stream()` for async."""
        from .validators import validate_prompt as _vp, validate_size as _vs  # noqa
        prompt = _vp(prompt)
        size = self.validate_size(kwargs.get("size") or self.config.default_size)
        kwargs["size"] = size

        payload = self.build_payload(prompt, **kwargs)
        data = http_sync.post_json(
            self.endpoint(),
            payload,
            api_key=self.config.api_key,
            auth_header=self.config.auth_header_name,
            timeout=self.config.timeout,
        )
        resp = self.parse_response(data)
        self._save_all(resp)
        return resp

    def stream(self, prompt: str, **kwargs) -> AsyncIterator[ImageResult]:
        """Async streaming. Override if the provider supports SSE.

        The default implementation runs the async path in a worker thread
        (so it's safe to call from sync code) and yields ImageResult objects
        as they arrive. Providers that want native async override this.
        """
        from .validators import validate_prompt as _vp
        prompt = _vp(prompt)
        size = self.validate_size(kwargs.get("size") or self.config.default_size)
        kwargs["size"] = size
        kwargs["stream"] = True
        payload = self.build_payload(prompt, **kwargs)

        from . import http_async

        save_dir = self.config.save_dir

        async def _gen() -> AsyncIterator[ImageResult]:
            from .http_async import async_stream
            idx = 0
            async for event in async_stream(
                self.endpoint(),
                payload,
                api_key=self.config.api_key,
                auth_header=self.config.auth_header_name,
                timeout=self.config.timeout,
            ):
                for entry in (event.get("data") or []):
                    if entry.get("error"):
                        from .errors import classify
                        err = entry["error"]
                        raise classify(err.get("code", "Unknown"),
                                       err.get("message", "stream error"))
                    idx += 1
                    # `data` may carry partial url or b64_json per chunk.
                    path = _save_streamed_entry(entry, save_dir, idx,
                                                self.config.output_format)
                    yield ImageResult(path=path, size=entry.get("size"))

        # Expose as an async generator by returning the coroutine that
        # produces one. Callers must iterate.
        return _gen()  # type: ignore[return-value]

    # ---- saving -----------------------------------------------------------

    def _save_all(self, response: GenerateResponse) -> None:
        """Walk the response, download/decode every image, populate `path`."""
        for i, entry in enumerate(response.raw.get("data") or [], 1):
            if i > len(response.images):
                break
            img = response.images[i - 1]
            if img.error or not entry:
                continue
            try:
                img.path = _save_data_entry(
                    entry, self.config.save_dir, i, self.config.output_format
                )
            except Exception as e:
                img.error = str(e)


# ---- GenericOpenAICompatibleProvider -----------------------------------------

class GenericOpenAICompatibleProvider(Provider):
    """Default implementation for OpenAI-style /v1/images/generations endpoints.

    Used for OpenAI gpt-image-1 / dall-e-3, and as the runtime wrapper for
    YAML-only providers that don't have a dedicated Python class.
    """

    name = "openai-compatible"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt.strip(),
        }
        # Map internal field names to provider field names
        rf = self.config.request_fields
        if "size" in kwargs and kwargs["size"]:
            payload[rf.get("size", "size")] = kwargs["size"]
        if kwargs.get("n"):
            payload[rf.get("n", "n")] = int(kwargs["n"])
        if kwargs.get("image") is not None:
            raw = normalize_image(kwargs["image"])
            if self.config.multi_image and not isinstance(raw, list):
                raw = [raw]
            field = self.config.image_field
            payload[rf.get("image", field)] = raw
        # Always include response_format so we know how to read the result
        payload[rf.get("response_format", "response_format")] = \
            kwargs.get("response_format", "url")
        # extra_params lets the user pin provider-specific fields
        payload.update(self.config.extra_params)
        payload.update(kwargs.get("extra") or {})
        return payload

    def parse_response(self, data: Dict[str, Any]) -> GenerateResponse:
        if data.get("error"):
            from .errors import classify
            err = data["error"]
            raise classify(err.get("code", "Unknown"), err.get("message", "unknown"))
        model = data.get("model", self.config.model)
        created = int(data.get("created", time.time()))
        images: List[ImageResult] = []
        for entry in (data.get("data") or []):
            if entry.get("error"):
                images.append(ImageResult(
                    path=Path(""),
                    error=entry["error"].get("message") or entry["error"].get("code"),
                ))
            else:
                # We don't have a real path yet — `generate()` will fill it in.
                images.append(ImageResult(path=Path(""), size=entry.get("size")))
        return GenerateResponse(model=model, created=created, images=images, raw=data)

    def validate_size(self, size: Optional[str]) -> str:
        # OpenAI default: any reasonable size passes; the server will reject.
        if not size:
            return self.config.default_size or "1024x1024"
        return str(size)


# ---- helpers used by both subclasses and generic provider ---------------------

def _make_filename(save_dir: Union[str, Path], idx: int, ext: str) -> Path:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return save_dir / f"{ts}_{idx:02d}_{suffix}{ext}"


def _save_data_entry(
    entry: Dict[str, Any], save_dir, idx: int, output_format: str
) -> Path:
    if "b64_json" in entry and entry["b64_json"]:
        data = base64.b64decode(entry["b64_json"])
        ext = ".png" if output_format == "png" else ".jpg"
        path = _make_filename(save_dir, idx, ext)
        path.write_bytes(data)
        return path
    if "url" in entry and entry["url"]:
        ext = ".png" if output_format == "png" else ".jpg"
        path = _make_filename(save_dir, idx, ext)
        http_sync.download_to(entry["url"], path)
        return path
    raise GenerateError(f"image entry has neither url nor b64_json: {entry}")


def _save_streamed_entry(
    entry: Dict[str, Any], save_dir, idx: int, output_format: str
) -> Path:
    """Same as _save_data_entry but tolerates partial SSE chunks."""
    return _save_data_entry(entry, save_dir, idx, output_format)
