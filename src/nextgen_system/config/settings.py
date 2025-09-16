"""Configuration loader for the next-generation system."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

_ENV_PREFIX = "NEXTGEN"
_DEFAULT_PROFILE = "defaults"
_PROFILE_ENV_VAR = f"{_ENV_PREFIX}__PROFILE"


def _expand_env(value: Any) -> Any:
    """Recursively expand environment variables in strings."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        if path.suffix in {".yaml", ".yml"} and yaml is not None:
            with path.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        else:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
    except FileNotFoundError:
        return {}
    return _expand_env(raw)


@dataclass(frozen=True)
class Settings:
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self.data
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key)
            if node is None:
                return default
        return node

    def replace(self, **updates: Any) -> "Settings":
        new_data = _deep_merge(self.data, updates)
        return replace(self, data=new_data)

    def dump(self) -> Dict[str, Any]:
        return self.data


_settings_singleton: Optional[Settings] = None


def load_settings(profile: Optional[str] = None, *, project_root: Optional[Path] = None) -> Settings:
    global _settings_singleton
    if _settings_singleton is not None and profile is None:
        return _settings_singleton

    config_dir = Path(__file__).resolve().parent
    env_root = os.environ.get("PROJECT_ROOT")
    if project_root is not None:
        resolved_project_root = project_root
    elif env_root:
        resolved_project_root = Path(env_root)
    else:
        package_root = config_dir.parent
        src_root = package_root.parent
        # When installed as a package the immediate parent is "src", otherwise fall back to package root.
        resolved_project_root = src_root.parent if src_root.name == "src" else package_root

    project_root = resolved_project_root

    defaults = _load_config(config_dir / "defaults.json")
    if not defaults:
        defaults = _load_config(config_dir / "defaults.yaml")

    chosen_profile = profile or os.environ.get(_PROFILE_ENV_VAR, _DEFAULT_PROFILE)
    profile_path_json = config_dir / "profiles" / f"{chosen_profile}.json"
    profile_path_yaml = config_dir / "profiles" / f"{chosen_profile}.yaml"
    profile_data = _load_config(profile_path_json)
    if not profile_data:
        profile_data = _load_config(profile_path_yaml)

    merged = _deep_merge(defaults, profile_data)

    # Apply environment overrides: NEXTGEN__SECTION__KEY=value
    env_overrides: Dict[str, Any] = {}
    prefix = f"{_ENV_PREFIX}__"
    for name, value in os.environ.items():
        if not name.startswith(prefix):
            continue
        keys = name[len(prefix):].lower().split("__")
        cursor = env_overrides
        for key in keys[:-1]:
            cursor = cursor.setdefault(key, {})
        cursor[keys[-1]] = value

    merged = _deep_merge(merged, env_overrides)

    # Normalise paths (relative to project root)
    paths = merged.get("paths", {})
    for key, path_value in list(paths.items()):
        if isinstance(path_value, str):
            if path_value in {"${PROJECT_ROOT}", "$PROJECT_ROOT"}:
                resolved_path = project_root
            else:
                candidate = Path(path_value)
                resolved_path = candidate if candidate.is_absolute() else project_root / candidate
            paths[key] = str(resolved_path.resolve())
    merged["paths"] = paths

    settings = Settings(data=merged)
    if profile is None:
        _settings_singleton = settings
    return settings


# Default export for convenience
settings = load_settings()

__all__ = ["Settings", "settings", "load_settings"]
