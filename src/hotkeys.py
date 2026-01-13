"""Global hotkey handling for X11 and Wayland."""

import threading
from typing import Optional, Callable

from .config import config, get_display_server
from .logging_utils import get_logger

logger = get_logger("hotkeys")


class HotkeyManager:
    """Manages global hotkeys."""

    def __init__(self):
        self._display_server = get_display_server()
        self._hotkey_listener = None
        self._key_listener = None
        self._running = False
        self._lock = threading.Lock()

        # Callbacks
        self._on_toggle: Optional[Callable[[], None]] = None
        self._on_cancel: Optional[Callable[[], None]] = None
        self._on_copy: Optional[Callable[[], None]] = None
        self._on_paste: Optional[Callable[[], None]] = None
        self._on_hide: Optional[Callable[[], None]] = None

    def set_callbacks(
        self,
        on_toggle: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        on_copy: Optional[Callable[[], None]] = None,
        on_paste: Optional[Callable[[], None]] = None,
        on_hide: Optional[Callable[[], None]] = None,
    ):
        """Set callback functions for hotkey events."""
        self._on_toggle = on_toggle
        self._on_cancel = on_cancel
        self._on_copy = on_copy
        self._on_paste = on_paste
        self._on_hide = on_hide

    def start(self) -> bool:
        """
        Start listening for global hotkeys.

        Returns:
            True if started successfully
        """
        with self._lock:
            if self._running:
                return True

            if self._display_server != "x11":
                logger.warning(
                    f"Global hotkeys not supported on {self._display_server}. "
                    "Use system hotkey settings to bind to whisper-trigger"
                )
                return False

            try:
                from pynput import keyboard

                # Setup toggle + copy/paste/hide as global combos
                hotkeys = {}
                toggle_hotkey = config.settings.hotkey_toggle
                if toggle_hotkey and self._on_toggle:
                    hotkeys[toggle_hotkey] = self._on_toggle
                if self._on_copy:
                    hotkeys["<ctrl>+<alt>+c"] = self._on_copy
                if self._on_paste:
                    hotkeys["<ctrl>+<alt>+v"] = self._on_paste
                if self._on_hide:
                    hotkeys["<ctrl>+<alt>+h"] = self._on_hide

                if hotkeys:
                    try:
                        self._hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
                        self._hotkey_listener.start()
                        logger.info(f"Hotkeys registered: {', '.join(hotkeys.keys())}")
                    except Exception as e:
                        logger.error(f"Failed to register hotkeys: {e}")

                # Setup cancel key (single key like Escape)
                cancel_hotkey = config.settings.hotkey_cancel
                if cancel_hotkey and self._on_cancel:
                    cancel_key = self._parse_single_key(cancel_hotkey)
                    if cancel_key:

                        def on_press(key):
                            if key == cancel_key:
                                self._on_cancel()

                        self._key_listener = keyboard.Listener(on_press=on_press)
                        self._key_listener.start()
                        logger.info(f"Cancel key registered: {cancel_hotkey}")

                self._running = True
                logger.info("Hotkey listener started")
                return True

            except Exception as e:
                logger.error(f"Failed to start hotkey listener: {e}")
                return False

    def _parse_single_key(self, key_str: str):
        """Parse single key string to pynput Key."""
        try:
            from pynput.keyboard import Key

            key_str = key_str.lower().strip()

            # Remove angle brackets if present
            if key_str.startswith("<") and key_str.endswith(">"):
                key_str = key_str[1:-1]

            key_map = {
                "escape": Key.esc,
                "esc": Key.esc,
                "space": Key.space,
                "enter": Key.enter,
                "return": Key.enter,
                "tab": Key.tab,
                "backspace": Key.backspace,
                "delete": Key.delete,
                "f1": Key.f1,
                "f2": Key.f2,
                "f3": Key.f3,
                "f4": Key.f4,
                "f5": Key.f5,
                "f6": Key.f6,
                "f7": Key.f7,
                "f8": Key.f8,
                "f9": Key.f9,
                "f10": Key.f10,
                "f11": Key.f11,
                "f12": Key.f12,
            }

            return key_map.get(key_str)

        except Exception as e:
            logger.error(f"Failed to parse key '{key_str}': {e}")
            return None

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        with self._lock:
            if not self._running:
                return

            if self._hotkey_listener is not None:
                try:
                    self._hotkey_listener.stop()
                except Exception:
                    pass
                self._hotkey_listener = None

            if self._key_listener is not None:
                try:
                    self._key_listener.stop()
                except Exception:
                    pass
                self._key_listener = None

            self._running = False
            logger.info("Hotkey listener stopped")

    @property
    def is_running(self) -> bool:
        """Check if hotkey listener is running."""
        return self._running

    @property
    def display_server(self) -> str:
        """Get detected display server."""
        return self._display_server

    @staticmethod
    def is_supported() -> bool:
        """Check if global hotkeys are supported."""
        return get_display_server() == "x11"


def get_wayland_hotkey_instructions() -> str:
    """Get instructions for setting up hotkeys on Wayland."""
    return """
Global hotkeys are not directly supported on Wayland.
To set up hotkeys, configure your desktop environment:

GNOME:
  Settings -> Keyboard -> Keyboard Shortcuts -> Custom Shortcuts
  Command: whisper-trigger toggle

KDE Plasma:
  System Settings -> Shortcuts -> Custom Shortcuts
  Command: whisper-trigger toggle

Sway/i3:
  Add to config: bindsym $mod+r exec whisper-trigger toggle

The whisper-trigger command communicates with the running app via IPC.
""".strip()


# Global hotkey manager instance
hotkey_manager = HotkeyManager()
