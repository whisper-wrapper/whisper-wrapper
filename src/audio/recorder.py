"""Audio recording with VAD support and chunk callbacks."""

import collections
import threading
from typing import Optional, Callable, List
import numpy as np
from ..config import SAMPLE_RATE, PRE_BUFFER_MS, config
from ..logging_utils import get_logger
from .vad import VADProcessor
from .devices import list_devices
from .stream import open_stream_with_fallback
from .callback import CallbackState, process_audio_callback

logger = get_logger("audio.recorder")
PRE_BUFFER_FRAMES = int(SAMPLE_RATE * PRE_BUFFER_MS / 1000)
VAD_FRAME_MS = 30
VAD_FRAME_SAMPLES = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)


class AudioRecorder:
    def __init__(self):
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()
        self._pre_buffer: collections.deque = collections.deque(
            maxlen=PRE_BUFFER_FRAMES // VAD_FRAME_SAMPLES + 1
        )
        self._main_buffer: List[np.ndarray] = []
        self._vad: Optional[VADProcessor] = None
        self._state = CallbackState()
        self._on_audio_level: Optional[Callable[[float], None]] = None
        self._on_speech_start: Optional[Callable[[], None]] = None
        self._on_silence_timeout: Optional[Callable[[], None]] = None
        self._on_audio_chunk: Optional[Callable[[np.ndarray], None]] = None

    def set_callbacks(
        self,
        on_audio_level: Optional[Callable[[float], None]] = None,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_silence_timeout: Optional[Callable[[], None]] = None,
        on_audio_chunk: Optional[Callable[[np.ndarray], None]] = None,
    ):
        self._on_audio_level = on_audio_level
        self._on_speech_start = on_speech_start
        self._on_silence_timeout = on_silence_timeout
        self._on_audio_chunk = on_audio_chunk

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        if not self._recording:
            return
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        audio = audio.astype(np.float32)

        process_audio_callback(
            audio=audio,
            state=self._state,
            vad=self._vad,
            pre_buffer=self._pre_buffer,
            main_buffer=self._main_buffer,
            on_audio_level=self._on_audio_level,
            on_speech_start=self._on_speech_start,
            on_silence_timeout=self._on_silence_timeout,
            on_audio_chunk=self._on_audio_chunk,
        )

    def start(self, device: Optional[int] = None) -> bool:
        with self._lock:
            if self._recording:
                logger.warning("Already recording")
                return False
            self._pre_buffer.clear()
            self._main_buffer.clear()
            self._state.reset()
            self._vad = (
                VADProcessor(config.settings.vad_threshold)
                if config.settings.vad_enabled
                else None
            )
            resolved_device = device
            if resolved_device is None and config.settings.microphone:
                for dev in list_devices():
                    if config.settings.microphone in dev["name"]:
                        resolved_device = dev["index"]
                        break

        stream_info = open_stream_with_fallback(
            device=resolved_device,
            callback=self._audio_callback,
            blocksize=VAD_FRAME_SAMPLES,
        )

        if stream_info:
            stream, used_device = stream_info
            with self._lock:
                self._stream = stream
                self._recording = True
            logger.info(f"Recording started (device={used_device})")
            return True

        with self._lock:
            self._stream = None
            self._recording = False
        return False

    def stop(self) -> Optional[np.ndarray]:
        with self._lock:
            if not self._recording:
                return None
            self._recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error stopping stream: {e}")
                finally:
                    self._stream = None

            if self._main_buffer:
                audio = np.concatenate(self._main_buffer)
                logger.info(f"Recording stopped: {len(audio)/SAMPLE_RATE:.2f}s")
                return audio
            if self._pre_buffer:
                audio = np.concatenate(list(self._pre_buffer))
                logger.info(
                    f"Recording stopped (pre-buffer): {len(audio)/SAMPLE_RATE:.2f}s"
                )
                return audio
            logger.warning("No audio recorded")
            return None

    def cancel(self) -> None:
        with self._lock:
            self._recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                finally:
                    self._stream = None
            self._main_buffer.clear()
            self._pre_buffer.clear()
            logger.info("Recording cancelled")

    @property
    def is_recording(self) -> bool:
        return self._recording


recorder = AudioRecorder()
