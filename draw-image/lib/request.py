"""Provider-agnostic request dataclass. Optional convenience type for callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class GenerateRequest:
    """Common request shape. Providers map this to their own wire format."""
    prompt: str
    image: Union[str, Path, List[Union[str, Path]], None] = None
    size: Optional[str] = None
    response_format: str = "url"  # 'url' or 'b64_json'
    output_format: str = "jpeg"   # 'jpeg' or 'png'
    watermark: bool = True
    sequential: bool = False
    max_images: int = 15
    optimize_mode: Optional[str] = None  # 'standard' or 'fast'
    web_search: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
