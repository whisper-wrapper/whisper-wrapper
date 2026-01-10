# Whisper Wrapper

Lightweight tray app for voice-to-text on Linux using faster-whisper. Works on X11 and Wayland, auto-stops on silence, and injects text into the active window.

## Features
- Audio capture at 16 kHz with VAD auto-stop and pre-buffer.
- Lazy model loading (tiny/base/small/medium/large-v3), CPU/GPU selection, default model `medium`.
- Hotkeys: `Ctrl+Alt+R` (toggle), `Esc` (cancel) for X11; Wayland uses a system shortcut bound to `whisper-trigger toggle`.
- IPC client `whisper-trigger` for system hotkeys/scripts.
- Transparent overlay with statuses, download progress, and partial results.

## System Requirements
- Currently tested only on Debian-based distributions.
- Python 3.10+
- `portaudio19-dev`, `ffmpeg`, `libxcb-cursor0`
- (Optional GPU) NVIDIA driver + CUDA 12 compatible stack

## Install from Source
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # includes NVIDIA CUDA runtime wheels
# CPU-only (no NVIDIA wheels):
# pip install -r requirements-cpu.txt
python -m src.app
```

## Models, Sources, and Privacy
- Models are downloaded on demand by `faster-whisper` and cached under `~/.cache/whisper-wrapper/models/`.
- Model files are typically fetched from the Hugging Face Hub; the exact repo depends on the model name and `faster-whisper` defaults.
- Whisper model weights have their own licenses and terms; review the model card/license before redistribution.
- Audio is processed locally. The app does not upload audio; network access is only used to download models/metadata.

## Run and Hotkeys
- Main app: `python -m src.app` (tray icon appears).
- IPC client: `python trigger.py toggle|cancel|status`.
- Wayland: bind a system shortcut to `whisper-trigger toggle` (see settings hint).

## Build
- PyInstaller + DEB: `./build_deb.sh`
- Script fails if any `src/*.py` exceeds 250 lines (architecture rule).

## Licensing and Redistribution Notes
- This repository is GPL-3.0-or-later; dependencies have their own licenses.
- PyQt6 is GPL/commercial; this project uses the GPL option to remain compatible.
- NVIDIA CUDA runtime wheels (`nvidia-cudnn-cu12`, `nvidia-cublas-cu12`) are proprietary; redistribution may be restricted by NVIDIA terms.
- For easier redistribution, prefer CPU-only installs or make GPU deps optional for end users.

## License Compatibility Decision
- Project is GPL-3.0-or-later to align with PyQt6's GPL licensing.
- If you want a permissive license, migrate to PySide6 (LGPL) and relicense.
- If you need to distribute closed or commercial binaries with PyQt6, obtain a commercial PyQt license.

## Model Management
- Settings (Transcription) show whether the selected model is cached; you can download/update with progress or delete the cache.

## Development
- Metadata (name/version) in `src/meta.py`.
- Logs: `~/.config/whisper-wrapper/logs/`.
- Config: `~/.config/whisper-wrapper/config.json` (auto-created).
- Suggested checks: `pre-commit run --all-files` (ruff, black, mypy).
- Tests: `pip install -r requirements-ci.txt` then `pytest`.
