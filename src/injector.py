import shutil
import subprocess
import time
from typing import Optional, Tuple

from .config import get_display_server
from .logging_utils import get_logger

logger = get_logger("injector")


class TextInjector:
    def __init__(self):
        self._display_server = get_display_server()
        self._method: Optional[str] = None
        self._detect_method()

    def _detect_method(self) -> None:
        # For X11: use xclip + xdotool Ctrl+V (most reliable for Unicode/Cyrillic)
        if self._display_server == "x11":
            if shutil.which("xclip") and shutil.which("xdotool"):
                self._method = "xclip"
                logger.info("Using xclip + Ctrl+V for text injection (X11, Unicode)")
                return

        # For Wayland
        if shutil.which("wl-copy") and shutil.which("wtype"):
            self._method = "wl-copy"
            logger.info("Using wl-copy + Ctrl+V for text injection (Wayland)")
        elif shutil.which("wtype"):
            self._method = "wtype"
            logger.info("Using wtype for text injection (Wayland)")
        elif shutil.which("ydotool"):
            self._method = "ydotool"
            logger.info("Using ydotool for text injection")
        else:
            self._method = "clipboard"
            logger.warning("No typing tool available, using clipboard fallback")

    def _inject_xdotool(self, text: str) -> bool:
        try:
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(f"xdotool error: {result.stderr.decode()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("xdotool timed out")
            return False
        except Exception as e:
            logger.error(f"xdotool injection failed: {e}")
            return False

    def _inject_xclip(self, text: str) -> bool:
        try:
            # Save to clipboard using xclip
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-i"], stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode("utf-8"), timeout=2)

            if proc.returncode != 0:
                logger.error("xclip failed to copy")
                return False

            # Wait for clipboard to be ready
            time.sleep(0.15)

            # Simulate Ctrl+V using xdotool
            result = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                capture_output=True,
                timeout=2,
            )

            if result.returncode != 0:
                logger.error(f"xdotool key failed: {result.stderr.decode()}")
                return False

            return True

        except Exception as e:
            logger.error(f"xclip injection failed: {e}")
            return False

    def _inject_wtype(self, text: str) -> bool:
        try:
            result = subprocess.run(
                ["wtype", "--", text], capture_output=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"wtype error: {result.stderr.decode()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("wtype timed out")
            return False
        except Exception as e:
            logger.error(f"wtype injection failed: {e}")
            return False

    def _inject_ydotool(self, text: str) -> bool:
        try:
            result = subprocess.run(
                ["ydotool", "type", "--", text], capture_output=True, timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error("ydotool timed out")
            return False
        except Exception as e:
            logger.error(f"ydotool injection failed: {e}")
            return False

    def _inject_wl_copy(self, text: str) -> bool:
        try:
            # Copy to clipboard
            proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"), timeout=2)

            if proc.returncode != 0:
                return False

            time.sleep(0.05)

            # Try wtype for Ctrl+V, or ydotool
            if shutil.which("wtype"):
                result = subprocess.run(
                    ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                    capture_output=True,
                    timeout=2,
                )
                return result.returncode == 0
            elif shutil.which("ydotool"):
                result = subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],  # Ctrl+V
                    capture_output=True,
                    timeout=2,
                )
                return result.returncode == 0

            return False

        except Exception as e:
            logger.error(f"wl-copy injection failed: {e}")
            return False

    def _inject_clipboard(self, text: str) -> Tuple[bool, str]:
        try:
            import pyperclip

            pyperclip.copy(text)
            msg = "Text copied to clipboard (Ctrl+V to paste)"
            logger.info(msg)
            return True, msg
        except Exception as e:
            logger.error(f"Clipboard fallback failed: {e}")
            return False, f"Failed to copy: {e}"

    def inject(self, text: str) -> Tuple[bool, Optional[str]]:
        if not text:
            return True, None

        logger.debug(f"Injecting text ({len(text)} chars) via {self._method}")

        # Small delay to ensure window focus
        time.sleep(0.1)

        success = False
        message = None

        if self._method == "xdotool":
            success = self._inject_xdotool(text)
        elif self._method == "xclip":
            success = self._inject_xclip(text)
        elif self._method == "wtype":
            success = self._inject_wtype(text)
        elif self._method == "ydotool":
            success = self._inject_ydotool(text)
        elif self._method == "wl-copy":
            success = self._inject_wl_copy(text)

        # Fallback to clipboard if injection failed
        if not success or self._method == "clipboard":
            success, message = self._inject_clipboard(text)

        if success and not message:
            logger.info(f"Text injected successfully ({len(text)} chars)")

        return success, message

    @property
    def method(self) -> str:
        return self._method or "none"

    @property
    def display_server(self) -> str:
        return self._display_server


def check_tools() -> dict:
    tools = {
        "xdotool": shutil.which("xdotool") is not None,
        "xclip": shutil.which("xclip") is not None,
        "wtype": shutil.which("wtype") is not None,
        "ydotool": shutil.which("ydotool") is not None,
        "wl-copy": shutil.which("wl-copy") is not None,
    }

    # Check if ydotool daemon is running
    if tools["ydotool"]:
        try:
            result = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True)
            tools["ydotoold_running"] = result.returncode == 0
        except Exception:
            tools["ydotoold_running"] = False

    return tools


# Global injector instance
injector = TextInjector()
