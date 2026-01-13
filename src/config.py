"""Configuration management for Whisper GUI Wrapper."""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# Application constants (single source of truth in meta.py)
from .meta import APP_NAME

# Paths
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = Path.home() / ".cache" / APP_NAME
MODELS_DIR = CACHE_DIR / "models"
LOG_DIR = CONFIG_DIR / "logs"
LOCK_FILE = CONFIG_DIR / "app.lock"
IPC_SOCKET_NAME = f"{APP_NAME}-ipc"

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
PRE_BUFFER_MS = 400

# Available models
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Default hotkeys
DEFAULT_HOTKEY_TOGGLE = "<ctrl>+<alt>+r"
DEFAULT_HOTKEY_CANCEL = "escape"
OVERLAY_THEMES = ("auto", "dark", "light")


@dataclass
class Settings:
    """User settings with defaults."""

    microphone: Optional[str] = None  # None = system default
    vad_enabled: bool = True
    vad_silence_timeout: float = 1.5  # seconds (0.5-3.0)
    vad_threshold: int = 2  # webrtcvad aggressiveness (0-3)
    model_size: str = "medium"
    device: str = "auto"  # auto/cpu/cuda
    language: Optional[str] = None  # None = auto-detect
    hotkey_toggle: str = DEFAULT_HOTKEY_TOGGLE
    hotkey_cancel: str = DEFAULT_HOTKEY_CANCEL
    max_recording_sec: Optional[float] = None  # None disables hard cap
    overlay_theme: str = "auto"  # auto/dark/light
    overlay_opacity: float = 0.8
    auto_paste: bool = True

    def validate(self) -> None:
        """Validate and clamp settings to valid ranges."""
        self.vad_silence_timeout = max(0.5, min(3.0, self.vad_silence_timeout))
        self.vad_threshold = max(0, min(3, self.vad_threshold))
        if self.model_size not in AVAILABLE_MODELS:
            self.model_size = "medium"
        if self.device not in ("auto", "cpu", "cuda"):
            self.device = "auto"
        if self.max_recording_sec is not None:
            self.max_recording_sec = max(5.0, float(self.max_recording_sec))
        if self.overlay_theme not in OVERLAY_THEMES:
            self.overlay_theme = "auto"
        self.overlay_opacity = max(0.1, min(1.0, float(self.overlay_opacity)))
        self.auto_paste = bool(self.auto_paste)


class ConfigManager:
    """Manages loading and saving configuration."""

    def __init__(self):
        self._settings: Optional[Settings] = None
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create necessary directories."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def settings(self) -> Settings:
        """Get current settings, loading from file if needed."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings

    def load(self) -> Settings:
        """Load settings from config file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                settings = Settings(
                    **{
                        k: v
                        for k, v in data.items()
                        if k in Settings.__dataclass_fields__
                    }
                )
                settings.validate()
                return settings
            except (json.JSONDecodeError, TypeError):
                pass
        return Settings()

    def save(self, settings: Optional[Settings] = None) -> None:
        """Save settings to config file."""
        if settings is not None:
            self._settings = settings
        if self._settings is not None:
            self._settings.validate()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._settings), f, indent=2, ensure_ascii=False)

    def update(self, **kwargs) -> None:
        """Update specific settings."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()


# Global config instance
config = ConfigManager()


def is_wayland() -> bool:
    """Check if running under Wayland."""
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


def get_display_server() -> str:
    """Get current display server type."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return "wayland"
    elif session_type == "x11":
        return "x11"
    # Fallback detection
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"
