"""Audio input device helpers."""

from typing import List, Optional

from ..config import SAMPLE_RATE
from ..logging_utils import get_logger

logger = get_logger("audio.devices")


def list_devices() -> List[dict]:
    """List available audio input devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                inputs.append(
                    {
                        "index": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                        "default": dev.get("default_samplerate", SAMPLE_RATE),
                    }
                )
        return inputs
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return []


def get_default_device() -> Optional[int]:
    """Get default input device index."""
    try:
        import sounddevice as sd

        return sd.default.device[0]
    except Exception:
        return None
