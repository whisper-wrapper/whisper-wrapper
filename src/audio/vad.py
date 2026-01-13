"""Voice Activity Detection utilities."""

from ..config import SAMPLE_RATE
from ..logging_utils import get_logger

logger = get_logger("audio.vad")


class VADProcessor:
    """Voice Activity Detection using webrtcvad."""

    def __init__(self, aggressiveness: int = 2):
        self._vad = None
        self._aggressiveness = max(0, min(3, aggressiveness))
        self._init_vad()

    def _init_vad(self):
        """Initialize webrtcvad."""
        try:
            import webrtcvad

            self._vad = webrtcvad.Vad(self._aggressiveness)
            logger.info(f"VAD initialized (aggressiveness={self._aggressiveness})")
        except ImportError:
            logger.warning("webrtcvad not available, VAD disabled")
            self._vad = None

    def is_speech(self, audio_frame: bytes) -> bool:
        """Return True if speech is detected in the frame."""
        if self._vad is None:
            return True

        try:
            return self._vad.is_speech(audio_frame, SAMPLE_RATE)
        except Exception:
            return True
