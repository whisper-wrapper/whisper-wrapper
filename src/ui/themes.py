"""Theme helpers for UI components."""

from PyQt6.QtGui import QColor


def get_overlay_palette(theme: str) -> dict:
    """Return palette dict for overlay."""
    if theme == "light":
        return {
            "bg": QColor(248, 248, 248, 235),
            "text": "#1e1e1e",
            "muted": "rgba(0, 0, 0, 180)",
            "hint": "rgba(0, 0, 0, 160)",
            "accent": "#1976d2",
            "bar_bg": "rgba(0, 0, 0, 40)",
            "level_bg": "rgba(0, 0, 0, 20)",
        }
    return {
        "bg": QColor(14, 14, 18, 230),
        "text": "#f5f5f5",
        "muted": "rgba(255, 255, 255, 190)",
        "hint": "rgba(255, 255, 255, 170)",
        "accent": "#4cc2ff",
        "bar_bg": "rgba(255, 255, 255, 60)",
        "level_bg": "rgba(255, 255, 255, 35)",
    }
