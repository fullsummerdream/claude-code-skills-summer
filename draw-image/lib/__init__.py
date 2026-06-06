"""draw-image skill: multi-provider image generation library.

Public API:
  load_config(path) -> Config
  get_provider(config, name=None) -> ProviderConfig
  generate(prompt, **kwargs) -> GenerateResponse   (sync)
  stream(prompt, **kwargs)  -> AsyncIterator[ImageResult]
  mask_key(key) -> str   (utility for safe logging)
"""

from .base import Provider, mask_key
from .config import Config, ProviderConfig, load_config, get_provider as _get_provider_cfg
from .errors import (
    AuthenticationError,
    GenerateError,
    InternalServerError,
    InvalidParameterError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    SensitiveContentError,
)
from .registry import PROVIDERS, get_class, instantiate, register
from .request import GenerateRequest
from .response import GenerateResponse, ImageResult, ToolCall, Usage

# Importing the providers package triggers @register decorators for built-ins.
from . import providers as _providers  # noqa: F401

__all__ = [
    # core
    "Config",
    "ProviderConfig",
    "Provider",
    "load_config",
    "get_provider",
    "generate",
    "stream",
    "mask_key",
    "PROVIDERS",
    # data types
    "GenerateRequest",
    "GenerateResponse",
    "ImageResult",
    "Usage",
    "ToolCall",
    # errors
    "GenerateError",
    "InvalidParameterError",
    "AuthenticationError",
    "NotFoundError",
    "QuotaExceededError",
    "RateLimitError",
    "SensitiveContentError",
    "InternalServerError",
]


# ---- high-level convenience functions ----------------------------------------

def generate(
    prompt: str,
    *,
    config: Config = None,
    config_path: str = None,
    provider: str = None,
    **kwargs,
) -> GenerateResponse:
    """Generate images synchronously. Reads config if not supplied.

    Args:
        prompt: text prompt.
        config: pre-loaded Config (skips disk read).
        config_path: path to config.yaml (defaults to <skill-dir>/config.yaml).
        provider: provider name override (defaults to config.default_provider).
        **kwargs: forwarded to the provider's build_payload
            (size, image, sequential, max_images, optimize_mode, web_search,
             response_format, output_format, watermark, extra, ...).
    """
    if config is None:
        from pathlib import Path
        import os
        if config_path is None:
            skill_dir = Path(__file__).resolve().parent.parent
            config_path = str(skill_dir / "config.yaml")
        config = load_config(config_path)
    spec = _get_provider_cfg(config, provider)
    prov = instantiate(spec.type, spec)
    return prov.generate(prompt, **kwargs)


def stream(prompt: str, *, config=None, config_path=None, provider=None, **kwargs):
    """Stream images asynchronously. Returns an async iterator."""
    if config is None:
        from pathlib import Path
        if config_path is None:
            skill_dir = Path(__file__).resolve().parent.parent
            config_path = str(skill_dir / "config.yaml")
        config = load_config(config_path)
    spec = _get_provider_cfg(config, provider)
    prov = instantiate(spec.type, spec)
    return prov.stream(prompt, **kwargs)


def get_provider(config: Config, name: str = None) -> Provider:
    """Get a live Provider instance from a Config object."""
    spec = _get_provider_cfg(config, name)
    return instantiate(spec.type, spec)
