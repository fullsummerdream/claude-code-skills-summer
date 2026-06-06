"""Data classes for image generation requests and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Usage:
    """Token usage from provider response."""
    generated_images: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    web_search_calls: int = 0  # volcengine only: usage.tool_usage.web_search


@dataclass
class ToolCall:
    """A tool invocation reported by the model."""
    type: str  # 'web_search'


@dataclass
class ImageResult:
    """One generated image."""
    path: Path
    size: Optional[str] = None  # e.g. "2048x2048"
    error: Optional[str] = None  # per-image error if the provider reported it


@dataclass
class GenerateResponse:
    """Full result of an image generation request."""
    model: str
    created: int
    images: List[ImageResult] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    tools: List[ToolCall] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def paths(self) -> List[Path]:
        """Successful image paths only."""
        return [img.path for img in self.images if img.path and not img.error]
