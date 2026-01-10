"""Application bootstrap and event loop."""

import os
import sys
from typing import Optional

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtWidgets import QApplication

from ..config import APP_NAME, APP_VERSION, LOCK_FILE, IPC_SOCKET_NAME, config, get_display_server, is_wayland
from ..hotkeys import hotkey_manager
from ..ipc_server import IpcServer
from ..logging_utils import setup_logging, get_logger
from ..model import transcriber
from ..system import acquire_lock, release_lock
from ..ui import overlay_manager, TrayController
from .recording import RecordingMixin
from .actions import UiActionsMixin

logger = get_logger("app")


class WhisperApp(QObject, RecordingMixin, UiActionsMixin):
    toggle_signal = pyqtSignal()
    cancel_signal = pyqtSignal()
    audio_level_signal = pyqtSignal(float)
    silence_timeout_signal = pyqtSignal()
    audio_chunk_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._app: Optional[QApplication] = None
        self._tray: Optional[TrayController] = None
        self._ipc: Optional[IpcServer] = None
        self._lock_handle = None
        self._recording = False
        self._processing = False
        self._worker_thread = None
        self._realtime_worker = None
        self._model_worker = None

        self.toggle_signal.connect(self._on_toggle)
        self.cancel_signal.connect(self._on_cancel)
        self.audio_level_signal.connect(self._on_audio_level)
        self.silence_timeout_signal.connect(self._on_silence_timeout)
        self.audio_chunk_signal.connect(self._on_audio_chunk)

    def _on_audio_level(self, level: float):
        overlay_manager.update_audio_level(level)

    def _on_silence_timeout(self):
        self._stop_recording()

    def _handle_ipc_command(self, command: str) -> str:
        if command == "toggle":
            self.toggle_signal.emit()
            return "ok"
        if command == "cancel":
            self.cancel_signal.emit()
            return "ok"
        if command == "status":
            return "recording" if self._recording else "idle"
        return "unknown command"

    def _setup_tray(self):
        self._tray = TrayController(
            app=self._app,
            on_toggle=lambda: self.toggle_signal.emit(),
            on_model_select=self._on_model_select,
            on_device_select=self._on_device_select,
            on_show_settings=self._show_settings,
            on_open_logs=self._open_logs_folder,
            on_quit=self._quit,
            current_model=config.settings.model_size,
            current_device=config.settings.device,
        )
        self._tray.setup_tray()

    def _setup_hotkeys(self, on_copy=None, on_paste=None, on_hide=None):
        hotkey_manager.set_callbacks(
            on_toggle=lambda: self.toggle_signal.emit(),
            on_cancel=lambda: self.cancel_signal.emit(),
            on_copy=on_copy,
            on_paste=on_paste,
            on_hide=on_hide,
        )
        hotkey_manager.start()

    def _start_ipc(self):
        self._ipc = IpcServer(IPC_SOCKET_NAME, self._handle_ipc_command, parent=self)
        self._ipc.start()

    def _attempt_toggle_running_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(IPC_SOCKET_NAME)
        if socket.waitForConnected(1000):
            socket.write(b"toggle")
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            logger.info("Sent toggle to running instance")
            return True
        return False

    def _quit(self):
        logger.info("Quitting...")
        if self._recording:
            from ..audio import recorder

            recorder.cancel()
        self._cleanup_realtime_worker(wait=True)
        if self._model_worker and self._model_worker.isRunning():
            self._model_worker.wait(500)
        if self._worker_thread is not None:
            if self._worker_thread.isRunning():
                self._worker_thread.wait(2000)
            self._worker_thread = None
        hotkey_manager.stop()
        if self._ipc:
            self._ipc.close()
        release_lock(self._lock_handle, LOCK_FILE)
        if self._app:
            self._app.quit()

    def run(self) -> int:
        setup_logging(debug=os.environ.get("DEBUG") == "1")
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        logger.info(
            "Environment: shell=%s desktop=%s session=%s display=%s wayland=%s",
            os.environ.get("SHELL", ""),
            os.environ.get("XDG_CURRENT_DESKTOP", ""),
            os.environ.get("DESKTOP_SESSION", ""),
            get_display_server(),
            is_wayland(),
        )

        self._lock_handle = acquire_lock(LOCK_FILE)
        if not self._lock_handle:
            return 0 if self._attempt_toggle_running_instance() else 1

        self._app = QApplication(sys.argv)
        self._app.setApplicationName(APP_NAME)
        self._app.setQuitOnLastWindowClosed(False)

        overlay_manager.initialize()
        overlay_manager.set_theme(config.settings.overlay_theme)
        overlay_manager.set_auto_paste(config.settings.auto_paste)
        overlay_manager.set_opacity(config.settings.overlay_opacity)
        self._setup_tray()
        self._start_ipc()
        self._setup_hotkeys(
            on_copy=self._copy_last_result,
            on_paste=self._paste_last_result,
            on_hide=self._hide_overlay,
        )
        overlay_manager.set_actions(
            on_copy=self._copy_last_result,
            on_paste=self._paste_last_result,
            on_hide=self._hide_overlay,
            on_auto_paste_change=self._on_auto_paste_toggle,
        )
        overlay_manager.set_toggle_action(on_toggle=lambda: self.toggle_signal.emit())
        self._start_model_load(config.settings.model_size)

        logger.info("Application ready")
        return self._app.exec()

    def _copy_last_result(self):
        try:
            import pyperclip
            if overlay_manager.overlay and overlay_manager.overlay._text_view:
                text = overlay_manager.overlay._text_view.toPlainText()
                if text:
                    pyperclip.copy(text)
                    overlay_manager.show_success("Copied to clipboard")
        except Exception as e:
            logger.error(f"Copy failed: {e}")

    def _paste_last_result(self):
        # Reuse injector to paste current text
        if overlay_manager.overlay and overlay_manager.overlay._text_view:
            text = overlay_manager.overlay._text_view.toPlainText()
            from ..injector import injector
            success, msg = injector.inject(text)
            if success and msg:
                overlay_manager.show_success(msg)
            elif not success:
                overlay_manager.show_error("Paste failed")

    def _hide_overlay(self):
        overlay_manager.hide()

    def _on_auto_paste_toggle(self, enabled: bool):
        config.update(auto_paste=enabled)
        overlay_manager.set_auto_paste(enabled)


def run_app() -> int:
    app = WhisperApp()
    return app.run()
