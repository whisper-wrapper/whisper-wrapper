"""Whisper transcription module with lazy model loading."""

import threading
from typing import Optional, Callable

import numpy as np

from ..config import MODELS_DIR, config, AVAILABLE_MODELS
from ..logging_utils import get_logger
from .device_selection import detect_device
from .models import TranscriptionResult
from .cache import is_model_cached

logger = get_logger("transcriber")


class Transcriber:
    def __init__(self):
        self._model = None
        self._model_name: Optional[str] = None
        self._device: Optional[str] = None
        self._lock = threading.Lock()
        self._loading = False

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def current_model(self) -> Optional[str]:
        return self._model_name

    @property
    def current_device(self) -> Optional[str]:
        return self._device

    def load_model(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        force_reload: bool = False,
    ) -> bool:
        with self._lock:
            if self._loading:
                logger.warning("Model loading already in progress")
                return False
            self._loading = True

        try:
            model_name = model_name or config.settings.model_size
            device = device or config.settings.device
            cached = is_model_cached(model_name)

            if model_name not in AVAILABLE_MODELS:
                logger.error(f"Invalid model: {model_name}")
                return False

            if (
                not force_reload
                and self._model is not None
                and self._model_name == model_name
                and self._device == device
            ):
                logger.info(f"Model {model_name} already loaded")
                if progress_callback:
                    progress_callback("ready", 100)
                return True

            if force_reload and self._model is not None:
                self.unload_model()

            def _report(status: str, percent: float):
                if progress_callback:
                    progress_callback(status, percent)

            actual_device, compute_type = detect_device(device)

            try:
                from faster_whisper import WhisperModel

                _report("loading_cached" if cached else "loading", 10)

                self._model = WhisperModel(
                    model_name,
                    device=actual_device,
                    compute_type=compute_type,
                    download_root=str(MODELS_DIR),
                )

                self._model_name = model_name
                self._device = actual_device

                _report("ready", 100)

                logger.info(f"Model loaded: {model_name} on {self._device}")
                return True

            except Exception as e:
                if actual_device == "cuda":
                    logger.warning(f"GPU loading failed: {e}, falling back to CPU")
                    _report("fallback_cpu", 50)
                    return self._load_cpu_fallback(model_name, progress_callback)
                raise

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            if progress_callback:
                progress_callback("error", 0)
            return False

        finally:
            with self._lock:
                self._loading = False

    def _load_cpu_fallback(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> bool:
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR),
            )
            self._model_name = model_name
            self._device = "cpu"

            if progress_callback:
                progress_callback("ready", 100)

            logger.info("Model loaded on CPU (fallback)")
            return True
        except Exception as e:
            logger.error(f"CPU fallback failed: {e}")
            return False

    def unload_model(self) -> None:
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                self._model_name = None
                self._device = None
                logger.info("Model unloaded")

    def _prepare_audio(self, audio: np.ndarray) -> np.ndarray:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val
        return audio

    def transcribe(
        self, audio: np.ndarray, language: Optional[str] = None
    ) -> Optional[TranscriptionResult]:
        if self._model is None:
            logger.error("Model not loaded")
            return None

        try:
            language = language or config.settings.language
            audio = self._prepare_audio(audio)
            logger.debug(f"Transcribing {len(audio)/16000:.2f}s of audio")

            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
            )

            text_parts = [segment.text.strip() for segment in segments]
            full_text = " ".join(text_parts).strip()

            result = TranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=info.language_probability,
                duration=info.duration,
            )

            logger.info(f"Transcribed: '{full_text[:50]}...' ({info.language})")
            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def transcribe_stream(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        on_partial: Optional[Callable[[str], None]] = None,
    ) -> Optional[TranscriptionResult]:
        if self._model is None:
            logger.error("Model not loaded")
            return None

        try:
            language = language or config.settings.language
            audio = self._prepare_audio(audio)
            logger.debug(f"Stream transcribing {len(audio)/16000:.2f}s of audio")

            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 100},
            )

            text_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    text_parts.append(text)
                    if on_partial:
                        on_partial(" ".join(text_parts))

            full_text = " ".join(text_parts).strip()

            return TranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=info.language_probability,
                duration=info.duration,
            )

        except Exception as e:
            logger.error(f"Stream transcription failed: {e}")
            return None


transcriber = Transcriber()
