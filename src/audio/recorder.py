"""Audio recording with VAD support and chunk callbacks."""

import collections
import threading
import time
from typing import Optional, Callable, List
import numpy as np
from ..config import SAMPLE_RATE, PRE_BUFFER_MS, config
from ..logging_utils import get_logger
from .vad import VADProcessor
from .devices import list_devices
from .chunks import emit_chunk_if_ready
from .stream import open_stream_with_fallback

logger = get_logger("audio.recorder")
PRE_BUFFER_FRAMES = int(SAMPLE_RATE * PRE_BUFFER_MS / 1000)
VAD_FRAME_MS = 30
VAD_FRAME_SAMPLES = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)
NON_VAD_SPEECH_START = 0.01
NON_VAD_SPEECH_STOP = 0.004


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
        self._silence_start: Optional[float] = None
        self._speech_detected = False
        self._timeout_triggered = False
        self._silence_start_nonvad: Optional[float] = None
        self._last_level_update: float = 0
        self._level_update_interval: float = 0.05
        self._last_activity_time: float = 0
        self._chunk_interval: float = 2.0
        self._last_chunk_time: float = 0
        self._last_chunk_index: int = 0
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
        current_time = time.time()
        rms = float(np.sqrt(np.mean(audio**2)))
        if self._last_activity_time == 0:
            self._last_activity_time = current_time
        if (
            self._on_audio_level
            and (current_time - self._last_level_update) >= self._level_update_interval
        ):
            self._on_audio_level(float(rms))
            self._last_level_update = current_time

        if np.abs(audio).max() > 0.99:
            logger.debug("Audio clipping detected")
        if config.settings.vad_enabled and self._vad is not None:
            audio_int16 = (audio * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            is_speech = self._vad.is_speech(audio_bytes)
            if is_speech:
                if not self._speech_detected:
                    self._speech_detected = True
                    logger.debug("Speech started")
                    if self._on_speech_start:
                        self._on_speech_start()
                    for prebuf in self._pre_buffer:
                        self._main_buffer.append(prebuf)
                    self._pre_buffer.clear()
                self._silence_start = None
                self._main_buffer.append(audio.copy())
                if rms >= NON_VAD_SPEECH_STOP:
                    self._last_activity_time = current_time
            else:
                if self._speech_detected:
                    if self._silence_start is None:
                        self._silence_start = time.time()
                    silence_duration = time.time() - self._silence_start
                    timeout = config.settings.vad_silence_timeout
                    if silence_duration >= timeout and not self._timeout_triggered:
                        logger.debug(f"Silence timeout ({timeout}s)")
                        self._timeout_triggered = True
                        if self._on_silence_timeout:
                            self._on_silence_timeout()
                    else:
                        self._main_buffer.append(audio.copy())
                else:
                    self._pre_buffer.append(audio.copy())
        else:
            if rms >= NON_VAD_SPEECH_START:
                if not self._speech_detected:
                    self._speech_detected = True
                    if self._on_speech_start:
                        self._on_speech_start()
                    for prebuf in self._pre_buffer:
                        self._main_buffer.append(prebuf)
                    self._pre_buffer.clear()
                self._silence_start_nonvad = None
                self._main_buffer.append(audio.copy())
                self._last_activity_time = current_time
            elif self._speech_detected:
                if self._silence_start_nonvad is None:
                    self._silence_start_nonvad = current_time
                elif (
                    (current_time - self._silence_start_nonvad)
                    >= config.settings.vad_silence_timeout
                    and not self._timeout_triggered
                ):
                    self._timeout_triggered = True
                    if self._on_silence_timeout:
                        self._on_silence_timeout()
                self._main_buffer.append(audio.copy())
            else:
                self._pre_buffer.append(audio.copy())

        if not self._timeout_triggered and config.settings.max_recording_sec:
            total_samples = sum(len(buf) for buf in self._main_buffer)
            max_samples = SAMPLE_RATE * config.settings.max_recording_sec
            if total_samples >= max_samples:
                logger.warning(
                    f"Max recording duration ({config.settings.max_recording_sec}s) reached"
                )
                self._timeout_triggered = True
                if self._on_silence_timeout:
                    self._on_silence_timeout()
        if self._speech_detected and not self._timeout_triggered:
            if (
                current_time - self._last_activity_time
            ) >= config.settings.vad_silence_timeout:
                self._timeout_triggered = True
                if self._on_silence_timeout:
                    self._on_silence_timeout()

        if self._on_audio_chunk and self._speech_detected:
            current_time = time.time()
            self._last_chunk_time, self._last_chunk_index = emit_chunk_if_ready(
                buffers=self._main_buffer,
                last_time=self._last_chunk_time,
                last_index=self._last_chunk_index,
                current_time=current_time,
                chunk_interval=self._chunk_interval,
                sample_rate=SAMPLE_RATE,
                on_audio_chunk=self._on_audio_chunk,
            )

    def start(self, device: Optional[int] = None) -> bool:
        with self._lock:
            if self._recording:
                logger.warning("Already recording")
                return False
            self._pre_buffer.clear()
            self._main_buffer.clear()
            self._silence_start = None
            self._speech_detected = False
            self._timeout_triggered = False
            self._silence_start_nonvad = None
            self._last_level_update = 0
            self._last_chunk_time = 0
            self._last_chunk_index = 0
            self._last_activity_time = 0
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
                    f"Recording stopped (pre-buffer only): {len(audio)/SAMPLE_RATE:.2f}s"
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
