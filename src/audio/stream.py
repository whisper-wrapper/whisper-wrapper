"""Helpers for opening audio streams with fallback."""

from typing import Optional, Callable

from ..config import SAMPLE_RATE, CHANNELS
from ..logging_utils import get_logger

logger = get_logger("audio.stream")


def open_stream_with_fallback(
    device: Optional[int],
    callback: Callable,
    blocksize: int,
) -> Optional[tuple]:
    """
    Try to open stream on preferred device, then fallback to default.

    Returns (stream, used_device) or None.
    """
    devices_to_try: list[Optional[int]] = [device] if device is not None else [None]
    if device is not None:
        devices_to_try.append(None)

    for idx, dev in enumerate(devices_to_try):
        try:
            import sounddevice as sd

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=blocksize,
                device=dev,
                callback=callback,
            )
            stream.start()
            return stream, dev
        except Exception as e:
            logger.error(f"Failed to start recording with device={dev}: {e}")
            if idx < len(devices_to_try) - 1:
                logger.info("Retrying with default input device...")
                continue
    return None
