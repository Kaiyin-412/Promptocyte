"""YAML policy resolution for Promptocyte.

Priority is explicit path, then PROMPTOCYTE_CONFIG, then the package default.
User files are merged over defaults so a deployment can override one policy value
without copying every safe default. The merged result is strictly validated.
"""
from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .config import GuardConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Promptocyte config file was not found: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Promptocyte config is not valid YAML: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Promptocyte config must contain a YAML mapping: {path}")
    return value


def _merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    result = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _upgrade_legacy(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept the pre-0.1 flat policy shape without making users rewrite files."""
    if not any(key in raw for key in ("allow_threshold", "warn_threshold", "enable_ml", "model_path")):
        return raw
    result = {key: value for key, value in raw.items() if key not in {"allow_threshold", "warn_threshold", "enable_ml", "model_path"}}
    security: dict[str, Any] = {}
    if "allow_threshold" in raw or "warn_threshold" in raw:
        security["risk_threshold"] = {"warn": int(raw.get("allow_threshold", 49)) + 1, "block": int(raw.get("warn_threshold", 79)) + 1}
    if security: result["security"] = security
    if "enable_ml" in raw or "model_path" in raw:
        result["ml"] = {key.replace("enable_", ""): value for key, value in raw.items() if key in {"enable_ml", "model_path"}}
        if "enable_ml" in raw:
            result["ml"]["enabled"] = result["ml"].pop("ml")
    return result


def _required(mapping: dict[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing required configuration field: {label}")
    return mapping[key]


def _bool(mapping: dict[str, Any], key: str, label: str) -> bool:
    value = _required(mapping, key, label)
    if not isinstance(value, bool):
        raise ValueError(f"Configuration field {label} must be true or false")
    return value


def _validate(raw: dict[str, Any]) -> GuardConfig:
    security = _required(raw, "security", "security")
    normalization = _required(raw, "normalization", "normalization")
    regex = _required(raw, "regex", "regex")
    ml = _required(raw, "ml", "ml")
    logging = _required(raw, "logging", "logging")
    if not all(isinstance(section, dict) for section in (security, normalization, regex, ml, logging)):
        raise ValueError("security, normalization, regex, ml, and logging must be YAML mappings")
    threshold = _required(security, "risk_threshold", "security.risk_threshold")
    if not isinstance(threshold, dict):
        raise ValueError("security.risk_threshold must be a mapping")
    block, warn = _required(threshold, "block", "security.risk_threshold.block"), _required(threshold, "warn", "security.risk_threshold.warn")
    if not isinstance(block, int) or not isinstance(warn, int) or not 0 <= warn < block <= 100:
        raise ValueError("risk thresholds must be integers satisfying 0 <= warn < block <= 100")
    level = _required(logging, "level", "logging.level")
    if not isinstance(level, str) or level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("logging.level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    return GuardConfig(
        # Existing decision logic compares `>` thresholds, so subtract one to keep
        # YAML block: 80 / warn: 50 inclusive at exactly those values.
        allow_threshold=warn - 1, warn_threshold=block - 1,
        enable_ml=_bool(ml, "enabled", "ml.enabled"),
        model_path=_required(ml, "model_path", "ml.model_path"),
        normalization_enabled=_bool(normalization, "enabled", "normalization.enabled"),
        regex_enabled=_bool(regex, "enabled", "regex.enabled"),
        logging_enabled=_bool(logging, "enabled", "logging.enabled"),
        logging_level=level.upper(),
    )


def load_config(path: str | Path | None = None) -> GuardConfig:
    """Load a validated config using explicit path > environment > package default."""
    default_file = files("promptocyte.config").joinpath("default.yaml")
    defaults = yaml.safe_load(default_file.read_text(encoding="utf-8"))
    requested = path if path is not None else os.environ.get("PROMPTOCYTE_CONFIG")
    if requested is None:
        return _validate(defaults)
    user_path = Path(requested).expanduser()
    return _validate(_merge(defaults, _upgrade_legacy(_read_yaml(user_path))))
