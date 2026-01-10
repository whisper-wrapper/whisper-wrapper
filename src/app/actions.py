"""UI actions and settings handlers."""

import subprocess
from typing import Optional

from PyQt6.QtWidgets import QMessageBox, QSystemTrayIcon

from ..config import APP_NAME, LOG_DIR, config
from ..hotkeys import hotkey_manager, get_wayland_hotkey_instructions
from ..logging_utils import get_logger
from ..ui import overlay_manager, SettingsDialog
from ..model import transcriber, is_model_cached
from .workers import ModelLoadWorker

logger = get_logger("app.ui")


class UiActionsMixin:
    _model_worker: Optional[ModelLoadWorker]

    def _update_toggle_action(self):
        if self._tray:
            self._tray.update_toggle_action(self._recording)

    def _on_model_select(self, model: str):
        config.update(model_size=model)
        if self._tray:
            self._tray.set_model(model)
        if transcriber.current_model != model:
            transcriber.unload_model()
        self._start_model_load(model)
        logger.info(f"Model changed to: {model}")

    def _on_device_select(self, device: str):
        config.update(device=device)
        transcriber.unload_model()
        if device in ("cuda", "auto"):
            transcriber.load_model()
            actual_device = transcriber.current_device
            if actual_device == "cpu" and device != "cpu" and self._tray:
                self._tray.notify(
                    APP_NAME,
                    "GPU unavailable, using CPU",
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000,
                )
                config.update(device="cpu")
                device = "cpu"
        if self._tray:
            self._tray.set_device(device)
        logger.info(f"Device changed to: {device}")

    def _start_model_load(self, model: str):
        self._cleanup_model_worker()
        cached = is_model_cached(model)
        overlay_manager.show_downloading(0, model, status="loading_cached" if cached else "loading")
        worker = ModelLoadWorker(model, config.settings.device, parent=self)
        worker.progress_signal.connect(
            lambda status, percent: overlay_manager.show_downloading(percent, model, status=status)
        )
        worker.finished_signal.connect(self._on_model_load_finished)
        worker.start()
        self._model_worker = worker

    def _on_model_load_finished(self, success: bool, error: str):
        self._model_worker = None
        if success:
            overlay_manager.show_success("Model ready")
            overlay_manager.set_status_detail(f"Model: {config.settings.model_size}")
        else:
            overlay_manager.show_error(error or "Model load failed")

    def _cleanup_model_worker(self):
        if hasattr(self, "_model_worker") and self._model_worker:
            worker = self._model_worker
            self._model_worker = None
            if worker.isRunning():
                worker.wait(100)

    def _show_settings(self):
        dialog = SettingsDialog()
        if dialog.exec():
            hotkey_manager.stop()
            hotkey_manager.set_callbacks(
                on_toggle=lambda: self.toggle_signal.emit(),
                on_cancel=lambda: self.cancel_signal.emit(),
            )
            hotkey_manager.start()
            if self._tray:
                self._tray.set_model(config.settings.model_size)
                self._tray.set_device(config.settings.device)
            overlay_manager.set_theme(config.settings.overlay_theme)
            overlay_manager.set_auto_paste(config.settings.auto_paste)
            overlay_manager.set_opacity(config.settings.overlay_opacity)

    def _open_logs_folder(self):
        subprocess.Popen(["xdg-open", str(LOG_DIR)])

    def _show_hotkey_info(self):
        QMessageBox.information(None, "Hotkey Setup", get_wayland_hotkey_instructions())
