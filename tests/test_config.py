import json

import pytest

from src import config as config_module


@pytest.fixture()
def config_paths(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    models_dir = cache_dir / "models"
    log_dir = config_dir / "logs"
    lock_file = config_dir / "app.lock"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(config_module, "MODELS_DIR", models_dir)
    monkeypatch.setattr(config_module, "LOG_DIR", log_dir)
    monkeypatch.setattr(config_module, "LOCK_FILE", lock_file)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    return config_file


def test_settings_validate_clamps_values():
    settings = config_module.Settings(
        vad_silence_timeout=0.1,
        vad_threshold=99,
        model_size="nope",
        device="gpu",
        max_recording_sec=2,
        overlay_theme="neon",
        overlay_opacity=2.5,
        auto_paste=0,
    )

    settings.validate()

    assert settings.vad_silence_timeout == 0.5
    assert settings.vad_threshold == 3
    assert settings.model_size == "medium"
    assert settings.device == "auto"
    assert settings.max_recording_sec == 5.0
    assert settings.overlay_theme == "auto"
    assert settings.overlay_opacity == 1.0
    assert settings.auto_paste is False


def test_config_manager_loads_and_saves(config_paths):
    manager = config_module.ConfigManager()
    settings = config_module.Settings(model_size="tiny", vad_silence_timeout=2.0)
    manager.save(settings)

    assert config_paths.exists()

    loaded = manager.load()
    assert loaded.model_size == "tiny"
    assert loaded.vad_silence_timeout == 2.0


def test_config_manager_ignores_unknown_keys(config_paths):
    config_paths.parent.mkdir(parents=True, exist_ok=True)
    config_paths.write_text(
        json.dumps({"model_size": "small", "extra_key": "ignored"}),
        encoding="utf-8",
    )

    manager = config_module.ConfigManager()
    loaded = manager.load()

    assert loaded.model_size == "small"
    assert not hasattr(loaded, "extra_key")


def test_config_manager_invalid_json_returns_defaults(config_paths):
    config_paths.parent.mkdir(parents=True, exist_ok=True)
    config_paths.write_text("{invalid", encoding="utf-8")

    manager = config_module.ConfigManager()
    loaded = manager.load()

    assert loaded.model_size == "medium"
