"""Model cache helpers."""

import shutil
from pathlib import Path
from typing import Set, List

from ..config import MODELS_DIR


def _model_dirs(model_name: str) -> List[Path]:
    """Return candidate cache dirs matching model name (direct or HF-style)."""
    if not MODELS_DIR.exists():
        return []
    matches = []
    for entry in MODELS_DIR.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name == model_name or name.endswith(f"-{model_name}") or model_name in name:
            matches.append(entry)
    return matches


def list_cached_models() -> Set[str]:
    if not MODELS_DIR.exists():
        return set()
    models = set()
    for entry in MODELS_DIR.iterdir():
        if entry.is_dir():
            name = entry.name
            if name.startswith("models--"):
                models.add(name.split("-")[-1])
            else:
                models.add(name)
    return models


def is_model_cached(model_name: str) -> bool:
    return bool(_model_dirs(model_name))


def remove_model_cache(model_name: str) -> bool:
    removed = False
    for path in _model_dirs(model_name):
        shutil.rmtree(path, ignore_errors=True)
        removed = True
    return removed
