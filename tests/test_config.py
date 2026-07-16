import pytest

from promptsentinel import SecurityGuard


def test_default_configuration_loads_from_package():
    guard = SecurityGuard()
    assert guard.config.allow_threshold == 49
    assert guard.config.warn_threshold == 79
    assert guard.config.enable_ml is True


def test_custom_configuration_is_merged_with_defaults(tmp_path):
    path = tmp_path / "custom.yaml"
    path.write_text("security:\n  risk_threshold:\n    block: 90\n    warn: 60\nml:\n  enabled: false\n", encoding="utf-8")
    guard = SecurityGuard(path)
    assert guard.config.allow_threshold == 59
    assert guard.config.warn_threshold == 89
    assert guard.config.enable_ml is False


def test_missing_configuration_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="PromptSentinel config file was not found"):
        SecurityGuard(tmp_path / "missing.yaml")


def test_environment_configuration_is_used(monkeypatch, tmp_path):
    path = tmp_path / "environment.yaml"
    path.write_text("ml:\n  enabled: false\n", encoding="utf-8")
    monkeypatch.setenv("PROMPTSENTINEL_CONFIG", str(path))
    assert SecurityGuard().config.enable_ml is False


def test_explicit_configuration_beats_environment(monkeypatch, tmp_path):
    environment = tmp_path / "environment.yaml"
    explicit = tmp_path / "explicit.yaml"
    environment.write_text("ml:\n  enabled: false\n", encoding="utf-8")
    explicit.write_text("ml:\n  enabled: true\n", encoding="utf-8")
    monkeypatch.setenv("PROMPTSENTINEL_CONFIG", str(environment))
    assert SecurityGuard(explicit).config.enable_ml is True
