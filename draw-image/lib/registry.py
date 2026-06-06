"""Provider registry. Decoration-based registration for built-in providers;
runtime construction for YAML-only providers.
"""

from __future__ import annotations

from typing import Dict, Type

from .base import GenericOpenAICompatibleProvider, Provider
from .errors import GenerateError

# Built-in providers register their CLASSES here on import.
# We store classes, not instances, because the instance needs the YAML config
# which is only loaded at call time.
PROVIDER_CLASSES: Dict[str, Type[Provider]] = {}


def register(cls: Type[Provider]) -> Type[Provider]:
    """Class decorator. Store the class by `cls.name` for later instantiation."""
    if not cls.name:
        raise ValueError(f"{cls.__name__}.name must be set")
    PROVIDER_CLASSES[cls.name] = cls
    return cls


def get_class(name: str) -> Type[Provider]:
    """Look up a registered provider class by name."""
    if name in PROVIDER_CLASSES:
        return PROVIDER_CLASSES[name]
    available = ", ".join(sorted(PROVIDER_CLASSES)) or "<none registered>"
    raise GenerateError(f"unknown provider: {name!r}. Available: {available}")


def instantiate(name: str, config) -> Provider:
    """Build a provider instance for a given name+config.

    - If `name` matches a built-in: use that class with the supplied config
      (allowing the YAML to override individual fields like base_url).
    - Otherwise: fall back to GenericOpenAICompatibleProvider, which handles
      any OpenAI-style endpoint via request_fields/response_fields mapping.
    """
    if name in PROVIDER_CLASSES:
        return PROVIDER_CLASSES[name](config)
    return GenericOpenAICompatibleProvider(config)


# Backwards-compat alias (old code may import PROVIDERS as if it's a dict of
# instances; keep it pointing at classes so len() and iteration still work).
PROVIDERS = PROVIDER_CLASSES
