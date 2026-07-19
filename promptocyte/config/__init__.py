"""Configuration models and package-owned default policy data."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardConfig:
    """Flat runtime view of the validated YAML policy."""
    allow_threshold: int
    warn_threshold: int
    enable_ml: bool
    model_path: str | None
    normalization_enabled: bool
    regex_enabled: bool
    logging_enabled: bool
    logging_level: str
