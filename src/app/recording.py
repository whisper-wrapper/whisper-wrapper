"""Recording and transcription behaviour for the app."""

from PyQt6.QtWidgets import QSystemTrayIcon

from ..audio import recorder
from ..injector import injector
from ..ui import overlay_manager
from .workers import TranscriptionWorker, RealtimeTranscriptionWorker
from ..model import transcriber
from ..config import APP_NAME, SAMPLE_RATE, config
from ..logging_utils import get_logger

logger = get_logger("app.recording")


class RecordingMixin:
    def _update_toggle_action(self, recording_state: bool | None = None):
        state = self._recording if recording_state is None else recording_state
        if self._tray:
            self._tray.update_toggle_action(state)

    def _on_audio_chunk(self, audio_data):
        if not self._recording:
            return
        self._cleanup_realtime_worker()
        worker = RealtimeTranscriptionWorker(audio_data, parent=self)
        worker.partial_result.connect(self._on_realtime_partial)
        worker.finished.connect(self._on_realtime_worker_finished)
        worker.start()
        self._realtime_worker = worker
        logger.debug(
            f"Realtime transcription started for {len(audio_data)/16000:.1f}s chunk"
        )

    def _on_realtime_partial(self, text: str):
        if self._recording:
            overlay_manager.show_transcribing(text)
            overlay_manager.update_partial_text(text)

    def _on_realtime_worker_finished(self):
        pass

    def _cleanup_realtime_worker(self, wait: bool = False):
        if self._realtime_worker is not None:
            worker = self._realtime_worker
            self._realtime_worker = None
            try:
                if hasattr(worker, "cancel"):
                    worker.cancel()
                if worker.isRunning():
                    if wait:
                        worker.wait(2000)
                    worker.finished.connect(worker.deleteLater)
                else:
                    worker.deleteLater()
            except RuntimeError:
                pass

    def _on_toggle(self):
        if self._processing:
            logger.debug("Processing in progress, ignoring toggle")
            return
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _on_cancel(self):
        if self._recording:
            self._cleanup_realtime_worker()
            recorder.cancel()
            self._recording = False
            self._update_toggle_action()
            if self._tray:
                self._tray.set_recording_indicator(False)
            overlay_manager.set_status_detail(
                f"Model: {config.settings.model_size} | Cancelled"
            )
            overlay_manager.set_stats("")
            logger.info("Recording cancelled")
        else:
            # Ensure tray icon resets if cancel is pressed while idle
            self._update_toggle_action()
            if self._tray:
                self._tray.set_recording_indicator(False)
                logger.info("Tray badge OFF (cancel idle)")

    def _start_recording(self):
        if self._recording:
            return
        recorder.set_callbacks(
            on_audio_level=lambda level: self.audio_level_signal.emit(level),
            on_silence_timeout=lambda: self.silence_timeout_signal.emit(),
            on_audio_chunk=lambda a: self.audio_chunk_signal.emit(a),
        )
        if recorder.start():
            self._recording = True
            self._update_toggle_action()
            if self._tray:
                self._tray.set_recording_indicator(True)
            overlay_manager.set_recording_state(True)
            overlay_manager.show_recording()
            self._last_duration = 0.0
            overlay_manager.set_status_detail(
                f"Model: {config.settings.model_size} | Recording (Esc to cancel)"
            )
            overlay_manager.set_stats("Listening... (Esc to cancel)")
            overlay_manager.set_hints("")
            logger.info("Recording started")
        else:
            overlay_manager.show_error("Failed to start recording")

    def _stop_recording(self):
        if not self._recording:
            return
        self._cleanup_realtime_worker(wait=True)
        audio = recorder.stop()
        self._recording = False
        self._update_toggle_action()
        if self._tray:
            self._tray.set_recording_indicator(False)
        overlay_manager.set_recording_state(False)
        if audio is None or len(audio) < 1600:
            overlay_manager.show_error("No audio recorded")
            return
        self._process_audio(audio)

    def _process_audio(self, audio):
        self._processing = True
        self._update_toggle_action(False)
        if self._tray:
            self._tray.set_recording_indicator(False)
        overlay_manager.set_recording_state(False)
        overlay_manager.show_transcribing()
        clip_duration = len(audio) / SAMPLE_RATE
        self._last_duration = clip_duration
        overlay_manager.set_hints("")
        device = transcriber.current_device or config.settings.device
        overlay_manager.set_status_detail(
            f"Model: {config.settings.model_size} | Transcribing"
        )
        overlay_manager.set_stats(f"Clip: {clip_duration:.1f}s | Device: {device}")
        logger.debug(f"Processing audio: {len(audio)} samples ({clip_duration:.2f}s)")
        worker = TranscriptionWorker(audio, parent=self)
        worker.finished_signal.connect(self._on_transcription_done)
        worker.progress_signal.connect(self._on_transcription_progress)
        worker.partial_signal.connect(self._on_partial_transcription)
        worker.finished.connect(self._on_worker_finished)
        worker.start()
        self._worker_thread = worker

    def _on_partial_transcription(self, text: str):
        overlay_manager.update_partial_text(text)

    def _on_worker_finished(self):
        logger.debug("Worker thread finished")
        if self._worker_thread:
            self._worker_thread.deleteLater()
            self._worker_thread = None

    def _on_transcription_progress(self, status: str, percent: float):
        if status in ("downloading", "loading", "initializing", "loading_cached"):
            overlay_manager.set_status_detail(
                f"Model: {config.settings.model_size} | Preparing"
            )
            overlay_manager.show_downloading(
                percent, config.settings.model_size, status=status
            )
        elif status == "fallback_cpu":
            overlay_manager.show_downloading(
                percent, config.settings.model_size, status=status
            )
            if self._tray:
                self._tray.notify(
                    APP_NAME,
                    "GPU not available, using CPU",
                    QSystemTrayIcon.MessageIcon.Warning,
                    2000,
                )
            overlay_manager.set_status_detail(
                f"Model: {config.settings.model_size} | GPU unavailable, loading on CPU"
            )

    def _on_transcription_done(self, result, error: str):
        self._processing = False
        # Reset tray indicator once processing completes
        self._update_toggle_action(False)
        if self._tray:
            self._tray.set_recording_indicator(False)
        overlay_manager.set_recording_state(False)
        if error:
            logger.error(f"Transcription failed: {error}")
            overlay_manager.show_error(error[:30])
            return
        if not result or not result.text:
            overlay_manager.show_error("Empty result")
            return
        overlay_manager.set_text(result.text)
        injected = False
        if config.settings.auto_paste:
            success, message = injector.inject(result.text)
            injected = success
            if success:
                if message:
                    overlay_manager.show_success(message)
                    if self._tray:
                        self._tray.notify(APP_NAME, message)
                else:
                    overlay_manager.show_success()
            else:
                overlay_manager.show_error("Injection failed")
        else:
            overlay_manager.show_success("Ready")
        overlay_manager.set_hints("")
        state_text = (
            "Inserted"
            if injected
            else ("Not inserted" if config.settings.auto_paste else "Ready")
        )
        overlay_manager.set_status_detail(
            f"Model: {config.settings.model_size} | {state_text}"
        )
        duration = result.duration or getattr(self, "_last_duration", 0.0)
        stats_parts = []
        if duration:
            stats_parts.append(f"Duration: {duration:.1f}s")
        if transcriber.current_device:
            stats_parts.append(f"Device: {transcriber.current_device}")
        if result.language:
            stats_parts.append(f"Lang: {result.language}")
        overlay_manager.set_stats(" | ".join(stats_parts) if stats_parts else "")
        self._update_toggle_action(False)
        if self._tray:
            self._tray.set_recording_indicator(False)
