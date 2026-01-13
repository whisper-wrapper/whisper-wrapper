"""Audio callback processing logic."""

import time
from typing import Optional, Callable, List
import numpy as np

from ..config import SAMPLE_RATE, config
from ..logging_utils import get_logger
from .vad import VADProcessor
from .chunks import emit_chunk_if_ready

logger = get_logger("audio.callback")

NON_VAD_SPEECH_START = 0.01
NON_VAD_SPEECH_STOP = 0.004


class CallbackState:
    """Mutable state for audio callback processing."""

    def __init__(self):
        self.silence_start: Optional[float] = None
        self.speech_detected = False
        self.timeout_triggered = False
        self.silence_start_nonvad: Optional[float] = None
        self.last_level_update: float = 0
        self.level_update_interval: float = 0.05
        self.last_activity_time: float = 0
        self.chunk_interval: float = 2.0
        self.last_chunk_time: float = 0
        self.last_chunk_index: int = 0

    def reset(self):
        self.__init__()


def process_audio_callback(
    audio: np.ndarray,
    state: CallbackState,
    vad: Optional[VADProcessor],
    pre_buffer,
    main_buffer: List[np.ndarray],
    on_audio_level: Optional[Callable[[float], None]],
    on_speech_start: Optional[Callable[[], None]],
    on_silence_timeout: Optional[Callable[[], None]],
    on_audio_chunk: Optional[Callable[[np.ndarray], None]],
) -> None:
    """Process a single audio callback frame."""
    current_time = time.time()
    rms = float(np.sqrt(np.mean(audio**2)))

    if state.last_activity_time == 0:
        state.last_activity_time = current_time

    if (
        on_audio_level
        and (current_time - state.last_level_update) >= state.level_update_interval
    ):
        on_audio_level(float(rms))
        state.last_level_update = current_time

    if np.abs(audio).max() > 0.99:
        logger.debug("Audio clipping detected")

    if config.settings.vad_enabled and vad is not None:
        _process_vad(
            audio,
            rms,
            current_time,
            state,
            vad,
            pre_buffer,
            main_buffer,
            on_speech_start,
            on_silence_timeout,
        )
    else:
        _process_non_vad(
            audio,
            rms,
            current_time,
            state,
            pre_buffer,
            main_buffer,
            on_speech_start,
            on_silence_timeout,
        )

    _check_timeouts(current_time, state, main_buffer, on_silence_timeout)
    _emit_chunks(current_time, state, main_buffer, on_audio_chunk)


def _process_vad(
    audio,
    rms,
    current_time,
    state,
    vad,
    pre_buffer,
    main_buffer,
    on_speech_start,
    on_silence_timeout,
):
    audio_int16 = (audio * 32767).astype(np.int16)
    is_speech = vad.is_speech(audio_int16.tobytes())

    if is_speech:
        if not state.speech_detected:
            state.speech_detected = True
            logger.debug("Speech started")
            if on_speech_start:
                on_speech_start()
            for prebuf in pre_buffer:
                main_buffer.append(prebuf)
            pre_buffer.clear()
        state.silence_start = None
        main_buffer.append(audio.copy())
        if rms >= NON_VAD_SPEECH_STOP:
            state.last_activity_time = current_time
    else:
        if state.speech_detected:
            if state.silence_start is None:
                state.silence_start = time.time()
            silence_duration = time.time() - state.silence_start
            timeout = config.settings.vad_silence_timeout
            if silence_duration >= timeout and not state.timeout_triggered:
                logger.debug(f"Silence timeout ({timeout}s)")
                state.timeout_triggered = True
                if on_silence_timeout:
                    on_silence_timeout()
            else:
                main_buffer.append(audio.copy())
        else:
            pre_buffer.append(audio.copy())


def _process_non_vad(
    audio,
    rms,
    current_time,
    state,
    pre_buffer,
    main_buffer,
    on_speech_start,
    on_silence_timeout,
):
    if rms >= NON_VAD_SPEECH_START:
        if not state.speech_detected:
            state.speech_detected = True
            if on_speech_start:
                on_speech_start()
            for prebuf in pre_buffer:
                main_buffer.append(prebuf)
            pre_buffer.clear()
        state.silence_start_nonvad = None
        main_buffer.append(audio.copy())
        state.last_activity_time = current_time
    elif state.speech_detected:
        if state.silence_start_nonvad is None:
            state.silence_start_nonvad = current_time
        elif (
            current_time - state.silence_start_nonvad
        ) >= config.settings.vad_silence_timeout and not state.timeout_triggered:
            state.timeout_triggered = True
            if on_silence_timeout:
                on_silence_timeout()
        main_buffer.append(audio.copy())
    else:
        pre_buffer.append(audio.copy())


def _check_timeouts(current_time, state, main_buffer, on_silence_timeout):
    if not state.timeout_triggered and config.settings.max_recording_sec:
        total_samples = sum(len(buf) for buf in main_buffer)
        max_samples = SAMPLE_RATE * config.settings.max_recording_sec
        if total_samples >= max_samples:
            logger.warning(
                f"Max recording duration ({config.settings.max_recording_sec}s) reached"
            )
            state.timeout_triggered = True
            if on_silence_timeout:
                on_silence_timeout()

    if state.speech_detected and not state.timeout_triggered:
        if (
            current_time - state.last_activity_time
        ) >= config.settings.vad_silence_timeout:
            state.timeout_triggered = True
            if on_silence_timeout:
                on_silence_timeout()


def _emit_chunks(current_time, state, main_buffer, on_audio_chunk):
    if on_audio_chunk and state.speech_detected:
        state.last_chunk_time, state.last_chunk_index = emit_chunk_if_ready(
            buffers=main_buffer,
            last_time=state.last_chunk_time,
            last_index=state.last_chunk_index,
            current_time=current_time,
            chunk_interval=state.chunk_interval,
            sample_rate=SAMPLE_RATE,
            on_audio_chunk=on_audio_chunk,
        )
