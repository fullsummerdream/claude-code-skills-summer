"""OpenAI-compatible provider. Wraps GenericOpenAICompatibleProvider
with OpenAI-specific request/response field defaults.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..base import GenericOpenAICompatibleProvider


class OpenAICompatibleProvider(GenericOpenAICompatibleProvider):
    name = "openai-compatible"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Use the generic implementation; defaults already match OpenAI shape.
        return super().build_payload(prompt, **kwargs)

    def parse_response(self, data: Dict[str, Any]) -> "GenerateResponse":
        return super().parse_response(data)

    def validate_size(self, size: Optional[str]) -> str:
        if not size:
            return self.config.default_size or "1024x1024"
        return str(size)


# Register class (not instance — config is supplied at call time).
from .. import registry
registry.register(OpenAICompatibleProvider)
