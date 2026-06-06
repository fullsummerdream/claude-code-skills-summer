"""Pydantic-based configuration loader.

Reads `config.yaml` next to the skill root, expands `${ENV_VAR}` placeholders,
validates each provider, and returns a structured Config object.

Uses Pydantic v2.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, Field, ValidationError, model_validator
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "draw-image requires pydantic>=2.0. Install with: pip install pydantic"
    ) from _e

try:
    import yaml
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "draw-image requires pyyaml. Install with: pip install pyyaml"
    ) from _e

from .errors import GenerateError


# ---- ProviderConfig ----------------------------------------------------------

class ProviderConfig(BaseModel):
    """One entry from config.yaml's `providers:` block."""
    type: str  # 'volcengine' | 'openai-compatible' | 'aliyun-bailian' | <custom>
    base_url: str
    api_key: Optional[str] = None
    model: str
    default_size: Optional[str] = None
    output_format: str = "jpeg"  # 'jpeg' or 'png'
    save_dir: Path = Field(default_factory=lambda: Path.home() / "Pictures" / "draw-image")
    timeout: float = 120.0
    requires_api_key: bool = True
    auth_header_name: str = "Authorization"
    request_fields: Dict[str, str] = Field(default_factory=dict)
    response_fields: Dict[str, str] = Field(default_factory=dict)
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    multi_image: bool = False  # True: always send image as a list
    image_field: str = "image"  # wire field name for reference images

    @model_validator(mode="after")
    def _expand_env_and_check_key(self) -> "ProviderConfig":
        unresolved = []
        if self.api_key:
            self.api_key = _expand_env(self.api_key)
            # Detect placeholders that couldn't be resolved — the
            # matching env var is not set. Force the check below.
            unresolved = _ENV_RE.findall(self.api_key)
            if unresolved:
                self.api_key = None
        if self.requires_api_key and not self.api_key:
            if unresolved:
                vars_list = ", ".join(f"${{{v}}}" for v in unresolved)
                raise ValueError(
                    f"api_key placeholder(s) not resolved: {vars_list}. "
                    f"Set the matching environment variable(s) or edit "
                    f"config.yaml directly."
                )
            raise ValueError(
                "api_key is required (set in config.yaml or via ${ENV_VAR})"
            )
        # Expand user paths
        self.save_dir = Path(os.path.expanduser(str(self.save_dir))).resolve()
        return self


class Config(BaseModel):
    providers: Dict[str, ProviderConfig]
    default_provider: str
    save_dir: Optional[Path] = None  # global default; per-provider overrides

    @model_validator(mode="after")
    def _check_default(self) -> "Config":
        if self.default_provider not in self.providers:
            raise ValueError(
                f"default_provider {self.default_provider!r} not in providers "
                f"{list(self.providers)}"
            )
        # If a global save_dir is set, propagate to any provider that didn't
        # override it.
        if self.save_dir:
            global_dir = Path(os.path.expanduser(str(self.save_dir))).resolve()
            for p in self.providers.values():
                # Only override if the provider kept the default.
                default_per_provider = Path.home() / "Pictures" / "draw-image"
                if p.save_dir == default_per_provider:
                    p.save_dir = global_dir
        return self


# ---- Loader ------------------------------------------------------------------

_ENV_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _expand_env(s: str) -> str:
    """Replace ${VAR} with os.environ[VAR] or leave as-is if unset.
    Unresolved placeholders are detected and reported by the caller."""
    def repl(m):
        var = m.group(1)
        val = os.environ.get(var)
        if val is None:
            return m.group(0)  # unresolved — caller will report this
        return val
    return _ENV_RE.sub(repl, s)


def load_config(path: Union[str, Path]) -> Config:
    """Load and validate config.yaml. Raises GenerateError on any problem."""
    p = Path(path)
    if not p.is_file():
        example = p.with_name("config.example.yaml")
        if example.is_file():
            import shutil
            shutil.copy(example, p)
            raise GenerateError(
                f"Created {p} from template.\n"
                f"Next steps:\n"
                f"  1. Edit this file and fill in your API keys.\n"
                f"  2. Re-run your command."
            )
        raise GenerateError(
            f"Config not found: {p}\n"
            f"Template {example} is also missing.\n"
            f"Make sure config.example.yaml exists in the skill directory."
        )
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise GenerateError(f"config.yaml parse error: {e}") from e
    if not isinstance(raw, dict) or "providers" not in raw:
        raise GenerateError("config.yaml must have a 'providers:' block")
    try:
        return Config(**raw)
    except ValidationError as e:
        # Pydantic v2 errors() is structured; flatten into a readable message.
        msgs = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            msgs.append(f"  - {loc}: {err.get('msg', 'invalid')}")
        raise GenerateError(
            "config.yaml validation failed:\n" + "\n".join(msgs)
        ) from e


def get_provider(config: Config, name: Optional[str] = None) -> ProviderConfig:
    """Resolve a provider by name (or default)."""
    name = name or config.default_provider
    if name not in config.providers:
        raise GenerateError(
            f"unknown provider {name!r}. Configured: {list(config.providers)}"
        )
    return config.providers[name]
