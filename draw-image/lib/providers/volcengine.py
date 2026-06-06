"""volcengine ARK provider (Doubao-Seedream-5.0-lite).

Supports: text-to-image, image-to-image (single + multi), sequential group
generation, web_search tool, jpeg/png output, watermark, streaming.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..base import Provider
from ..image_input import normalize_image
from .. import registry


@registry.register
class VolcengineProvider(Provider):  # noqa: F811 - intentional re-import shape
    name = "volcengine"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt.strip(),
            "size": kwargs.get("size") or self.config.default_size or "2048x2048",
            "response_format": kwargs.get("response_format", "url"),
            "output_format": kwargs.get("output_format", self.config.output_format),
            "watermark": kwargs.get("watermark", True),
            "sequential_image_generation":
                "auto" if kwargs.get("sequential") else "disabled",
            "stream": bool(kwargs.get("stream", False)),
        }
        if kwargs.get("image") is not None:
            raw = normalize_image(kwargs["image"])
            if self.config.multi_image and not isinstance(raw, list):
                raw = [raw]
            payload[self.config.image_field] = raw
        if kwargs.get("sequential"):
            payload["sequential_image_generation_options"] = {
                "max_images": int(kwargs.get("max_images", 15)),
            }
        om = kwargs.get("optimize_mode")
        if om is not None:
            payload["optimize_prompt_options"] = {"mode": om}
        if kwargs.get("web_search"):
            payload["tools"] = [{"type": "web_search"}]
        if kwargs.get("extra"):
            payload.update(kwargs["extra"])
        return payload

    def parse_response(self, data: Dict[str, Any]) -> "GenerateResponse":
        from ..errors import classify
        from ..response import GenerateResponse, ImageResult, ToolCall, Usage
        from pathlib import Path
        if data.get("error"):
            err = data["error"]
            raise classify(err.get("code", "Unknown"),
                           err.get("message", "unknown error"))
        import time
        model = data.get("model", self.config.model)
        created = int(data.get("created", time.time()))
        u = data.get("usage", {}) or {}
        tool_usage = u.get("tool_usage", {}) or {}
        usage = Usage(
            generated_images=int(u.get("generated_images", 0) or 0),
            output_tokens=int(u.get("output_tokens", 0) or 0),
            total_tokens=int(u.get("total_tokens", 0) or 0),
            web_search_calls=int(tool_usage.get("web_search", 0) or 0),
        )
        tools = [ToolCall(type=t.get("type", "")) for t in (data.get("tools") or [])]
        images = []
        for entry in (data.get("data") or []):
            if entry.get("error"):
                e = entry["error"]
                images.append(ImageResult(
                    path=Path(""),
                    size=entry.get("size"),
                    error=e.get("message") or e.get("code"),
                ))
            else:
                images.append(ImageResult(path=Path(""), size=entry.get("size")))
        return GenerateResponse(
            model=model, created=created, images=images, usage=usage,
            tools=tools, raw=data,
        )

    def validate_size(self, size: Optional[str]) -> str:
        from ..validators import validate_size as _vs
        return _vs(size, model=self.config.model)
