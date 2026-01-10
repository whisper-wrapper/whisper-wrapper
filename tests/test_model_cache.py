from src.model import cache as model_cache


def _setup_models_dir(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(model_cache, "MODELS_DIR", models_dir)
    return models_dir


def test_list_cached_models(tmp_path, monkeypatch):
    models_dir = _setup_models_dir(tmp_path, monkeypatch)
    (models_dir / "models--openai--small").mkdir()
    (models_dir / "base").mkdir()
    (models_dir / "note.txt").write_text("ignore", encoding="utf-8")

    cached = model_cache.list_cached_models()

    assert cached == {"small", "base"}


def test_remove_model_cache_removes_matches(tmp_path, monkeypatch):
    models_dir = _setup_models_dir(tmp_path, monkeypatch)
    match_a = models_dir / "models--openai--small"
    match_a.mkdir()
    (match_a / "file.bin").write_text("data", encoding="utf-8")
    match_b = models_dir / "custom-small"
    match_b.mkdir()
    keep = models_dir / "medium"
    keep.mkdir()

    assert model_cache.is_model_cached("small") is True
    assert model_cache.remove_model_cache("small") is True

    assert not match_a.exists()
    assert not match_b.exists()
    assert keep.exists()
    assert model_cache.remove_model_cache("tiny") is False
