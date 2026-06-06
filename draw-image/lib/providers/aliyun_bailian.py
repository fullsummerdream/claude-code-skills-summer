"""Aliyun Bailian (DashScope) image generation provider.

DashScope is OpenAI-API-compatible in many cases but has its own conventions
(model id format, response shape). The YAML config sets base_url to
https://dashscope.aliyuncs.com/api/v1 and supplies the right model id.
We treat it as a thin subclass of GenericOpenAICompatibleProvider with
aliyun-bailian-specific request tweaks.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..base import GenericOpenAICompatibleProvider


class AliyunBailianProvider(GenericOpenAICompatibleProvider):
    name = "aliyun-bailian"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Bailian's image generation endpoint accepts the OpenAI-style fields.
        # If the YAML supplies a different field mapping, respect it.
        return super().build_payload(prompt, **kwargs)

    def parse_response(self, data: Dict[str, Any]) -> "GenerateResponse":
        # DashScope's response nests results in `output.results` or `data`
        # depending on the API. The generic parser handles `data[]` shape.
        if "output" in data and isinstance(data["output"], dict):
            # Flatten output.choices / output.results into data[]
            out = data["output"]
            if "choices" in out:
                data = {**data, "data": [
                    {"url": c.get("message", {}).get("content", [{}])[0].get("image")}
                    if isinstance(c.get("message", {}).get("content"), list)
                    else c for c in out["choices"]
                ]}
        return super().parse_response(data)

    def validate_size(self, size: Optional[str]) -> str:
        if not size:
            return self.config.default_size or "1024x1024"
        return str(size)


from .. import registry
registry.register(AliyunBailianProvider)
