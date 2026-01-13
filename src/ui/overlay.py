"""Overlay manager facade."""

import os
import subprocess
from typing import Optional
from .overlay_widget import StatusOverlay
from .overlay_state import OverlayState


def _system_prefers_dark() -> bool:
    """Best-effort detection of dark preference on Linux desktops."""

    def _has_dark(text: str) -> bool:
        return "dark" in (text or "").lower()

    for env_var in ("GTK_THEME", "GNOME_THEME", "COLOR_SCHEME", "QT_STYLE_OVERRIDE"):
        if _has_dark(os.environ.get(env_var, "")):
            return True

    # GNOME/Ubuntu reports color-scheme
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        if result.returncode == 0 and _has_dark(result.stdout):
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        if result.returncode == 0 and _has_dark(result.stdout):
            return True
    except Exception:
        pass

    return False


class OverlayManager:
    def __init__(self):
        self._overlay: Optional[StatusOverlay] = None
        self._resolved_theme: str = "dark"
        self._actions: tuple = (None, None, None, None, None)
        self._auto_paste_enabled: bool = True

    def initialize(self) -> StatusOverlay:
        if self._overlay is None:
            self._overlay = StatusOverlay()
            self._overlay.set_theme(self._resolved_theme)
            copy_cb, paste_cb, hide_cb, auto_cb, toggle_cb = self._actions
            self._overlay.set_actions(copy_cb, paste_cb, hide_cb, auto_cb, toggle_cb)
            self._overlay.set_auto_paste(self._auto_paste_enabled)
            self._overlay.set_state(OverlayState.IDLE)
        return self._overlay

    @property
    def overlay(self) -> Optional[StatusOverlay]:
        return self._overlay

    def resolve_theme(self, preference: str) -> str:
        if preference == "auto":
            return "dark" if _system_prefers_dark() else "light"
        if preference in ("dark", "light"):
            return preference
        return "dark"

    def set_theme(self, preference: str):
        self._resolved_theme = self.resolve_theme(preference)
        if self._overlay:
            self._overlay.set_theme(self._resolved_theme)

    def set_actions(
        self, on_copy=None, on_paste=None, on_hide=None, on_auto_paste_change=None
    ):
        self._actions = (on_copy, on_paste, on_hide, on_auto_paste_change, None)
        if self._overlay:
            self._overlay.set_actions(
                on_copy, on_paste, on_hide, on_auto_paste_change, None
            )

    def set_toggle_action(self, on_toggle=None):
        copy_cb, paste_cb, hide_cb, auto_cb, _ = self._actions
        self._actions = (copy_cb, paste_cb, hide_cb, auto_cb, on_toggle)
        if self._overlay:
            self._overlay.set_actions(copy_cb, paste_cb, hide_cb, auto_cb, on_toggle)

    def set_auto_paste(self, enabled: bool):
        self._auto_paste_enabled = bool(enabled)
        if self._overlay:
            self._overlay.set_auto_paste(self._auto_paste_enabled)

    def set_recording_state(self, recording: bool):
        if self._overlay:
            self._overlay.set_recording_state(recording)

    def show_recording(self):
        if self._overlay:
            self._overlay.set_state(OverlayState.RECORDING)

    def show_processing(self):
        if self._overlay:
            self._overlay.set_state(OverlayState.PROCESSING)

    def show_transcribing(self, partial_text: str = ""):
        if self._overlay:
            self._overlay.set_state(OverlayState.TRANSCRIBING)
            if partial_text:
                self._overlay.set_text(partial_text)

    def update_partial_text(self, text: str):
        if self._overlay and self._overlay.state == OverlayState.TRANSCRIBING:
            self._overlay.set_text(text)

    def set_text(self, text: str):
        if self._overlay:
            self._overlay.set_text(text)

    def show_downloading(
        self, progress: float = 0, model: str = "", status: str = "loading"
    ):
        if self._overlay:
            if status == "downloading":
                message = f"Downloading {model}..." if model else "Downloading model..."
            elif status == "loading_cached":
                message = (
                    f"Loading cached {model}..." if model else "Loading cached model..."
                )
            elif status == "fallback_cpu":
                message = (
                    f"GPU unavailable, loading {model} on CPU..."
                    if model
                    else "GPU unavailable, loading on CPU..."
                )
            else:
                message = f"Loading {model}..." if model else "Loading model..."
            self._overlay.set_state(OverlayState.DOWNLOADING, message=message)
            self._overlay.set_progress(progress)

    def show_error(self, message: str):
        if self._overlay:
            self._overlay.show_temporary(OverlayState.ERROR, message, 3000)

    def show_success(self, message: Optional[str] = None):
        if self._overlay:
            self._overlay.show_temporary(OverlayState.SUCCESS, message, 5000)

    def hide(self):
        if self._overlay:
            self._overlay.hide_overlay()

    def update_audio_level(self, level: float):
        if self._overlay:
            self._overlay.set_audio_level(level)

    def update_progress(self, progress: float):
        if self._overlay:
            self._overlay.set_progress(progress)

    def set_hints(self, hints: str):
        if self._overlay:
            self._overlay.set_hints(hints)

    def set_opacity(self, opacity: float):
        if self._overlay:
            self._overlay.set_opacity(opacity)

    def set_status_detail(self, detail: str):
        if self._overlay:
            self._overlay.set_status_detail(detail)

    def set_stats(self, stats: str):
        if self._overlay:
            self._overlay.set_stats(stats)


overlay_manager = OverlayManager()
