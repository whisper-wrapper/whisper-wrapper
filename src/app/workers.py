"""Background workers for transcription and model loading."""

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from ..logging_utils import get_logger
from ..model import transcriber

logger = get_logger("workers")


class TranscriptionWorker(QThread):
    finished_signal = pyqtSignal(object, str)  # result, error
    progress_signal = pyqtSignal(str, float)  # status, percent
    partial_signal = pyqtSignal(str)  # partial text for real-time display

    def __init__(self, audio_data, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.audio_data = audio_data

    def run(self):
        try:
            logger.debug("Transcription worker started")
            if not transcriber.is_loaded:
                logger.debug("Loading model...")
                transcriber.load_model(
                    progress_callback=lambda s, p: self.progress_signal.emit(s, p)
                )

            logger.debug("Starting stream transcription...")
            result = transcriber.transcribe_stream(
                self.audio_data,
                on_partial=lambda text: self.partial_signal.emit(text),
            )

            if result and result.text:
                logger.debug(f"Transcription complete: {result.text[:50]}...")
                self.finished_signal.emit(result, "")
            else:
                logger.warning("Transcription returned empty")
                self.finished_signal.emit(None, "Transcription returned empty")
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            self.finished_signal.emit(None, str(e))


class RealtimeTranscriptionWorker(QThread):
    partial_result = pyqtSignal(str)

    def __init__(self, audio_data, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.audio_data = audio_data
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return

        try:
            if not transcriber.is_loaded:
                transcriber.load_model()

            if self._cancelled:
                return

            result = transcriber.transcribe(self.audio_data)

            if result and result.text and not self._cancelled:
                self.partial_result.emit(result.text)
        except Exception as e:
            logger.debug(f"Realtime transcription error: {e}")


class ModelLoadWorker(QThread):
    progress_signal = pyqtSignal(str, float)
    finished_signal = pyqtSignal(bool, str)  # success, error

    def __init__(self, model_name: str, device: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.model_name = model_name
        self.device = device

    def run(self):
        try:
            success = transcriber.load_model(
                model_name=self.model_name,
                device=self.device,
                progress_callback=lambda s, p: self.progress_signal.emit(s, p),
            )
            self.finished_signal.emit(
                bool(success), "" if success else "Model load failed"
            )
        except Exception as e:
            self.finished_signal.emit(False, str(e))
