"""UI layer exports."""

from .overlay_state import OverlayState, STATE_LABELS

__all__ = [
    "overlay_manager",
    "OverlayState",
    "STATE_LABELS",
    "TrayController",
    "SettingsDialog",
]


def __getattr__(name: str):
    """Lazy import PyQt6-dependent modules."""
    if name == "overlay_manager":
        from .overlay import overlay_manager

        return overlay_manager
    if name == "TrayController":
        from .tray import TrayController

        return TrayController
    if name == "SettingsDialog":
        from .settings import SettingsDialog

        return SettingsDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
