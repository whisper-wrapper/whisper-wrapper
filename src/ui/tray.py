"""System tray setup and helpers."""
from typing import Callable, Dict
from PyQt6.QtGui import QIcon, QAction, QPainter, QPixmap, QColor, QPen
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu

from ..config import APP_NAME, APP_VERSION, AVAILABLE_MODELS


class TrayController:
    def __init__(
        self,
        app,
        on_toggle: Callable[[], None],
        on_model_select: Callable[[str], None],
        on_device_select: Callable[[str], None],
        on_show_settings: Callable[[], None],
        on_open_logs: Callable[[], None],
        on_quit: Callable[[], None],
        current_model: str,
        current_device: str,
    ):
        self._app = app
        self._on_toggle = on_toggle
        self._on_model_select = on_model_select
        self._on_device_select = on_device_select
        self._on_show_settings = on_show_settings
        self._on_open_logs = on_open_logs
        self._on_quit = on_quit
        self._model_actions: Dict[str, QAction] = {}
        self._device_actions: Dict[str, QAction] = {}
        self._toggle_action: QAction | None = None
        self.tray: QSystemTrayIcon | None = None
        self._current_model = current_model
        self._current_device = current_device
        self._base_icon: QIcon | None = None
        self._recording_icon: QIcon | None = None
        self._is_recording: bool = False

    def _build_base_icon(self) -> QIcon:
        icon = QIcon.fromTheme("audio-input-microphone")
        if not icon.isNull():
            return icon

        # Simple fallback mic glyph
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(55, 55, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(6, 6, 52, 52)
        painter.setBrush(QColor(235, 235, 235))
        painter.drawRoundedRect(26, 16, 12, 24, 4, 4)
        painter.drawRect(28, 38, 8, 10)
        painter.setPen(QPen(QColor(235, 235, 235), 3))
        painter.drawLine(32, 48, 32, 56)
        painter.drawArc(18, 42, 28, 18, 0, 180 * 16)
        painter.end()
        return QIcon(pixmap)

    def _icon_with_badge(self, base_icon: QIcon) -> QIcon:
        pixmap = base_icon.pixmap(64, 64)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(220, 50, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        size = 14
        painter.drawEllipse(pixmap.width() - size - 6, pixmap.height() - size - 6, size, size)
        painter.end()
        return QIcon(pixmap)

    def _apply_icon(self, recording: bool):
        if not self.tray:
            return
        icon = self._recording_icon if recording else self._base_icon
        # Force a full reset on idle to avoid stale cached badges
        if not recording and self.tray:
            blank = QIcon(QPixmap(64, 64))
            self.tray.setIcon(blank)
        if icon:
            self.tray.setIcon(QIcon(icon.pixmap(64, 64)))
        self._is_recording = recording

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self._app)
        self._base_icon = self._build_base_icon()
        self._recording_icon = self._icon_with_badge(self._base_icon)
        self._apply_icon(False)

        self.tray.setToolTip(f"{APP_NAME} v{APP_VERSION}")
        menu = QMenu()

        self._toggle_action = QAction("Start Recording", menu)
        self._toggle_action.triggered.connect(self._on_toggle)
        menu.addAction(self._toggle_action)
        menu.addSeparator()

        model_menu = menu.addMenu("Model")
        for model in AVAILABLE_MODELS:
            action = QAction(model, model_menu)
            action.setCheckable(True)
            action.setChecked(model == self._current_model)
            action.triggered.connect(lambda checked, m=model: self._on_model_select(m))
            self._model_actions[model] = action
            model_menu.addAction(action)

        device_menu = menu.addMenu("Device")
        for device in ["auto", "cpu", "cuda"]:
            action = QAction(device.upper(), device_menu)
            action.setCheckable(True)
            action.setChecked(device == self._current_device)
            action.triggered.connect(lambda checked, d=device: self._on_device_select(d))
            self._device_actions[device] = action
            device_menu.addAction(action)

        menu.addSeparator()

        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self._on_show_settings)
        menu.addAction(settings_action)

        logs_action = QAction("Open Logs Folder", menu)
        logs_action.triggered.connect(self._on_open_logs)
        menu.addAction(logs_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._handle_activation)
        self.tray.show()

    def _handle_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_toggle()

    def update_toggle_action(self, recording: bool):
        if self._toggle_action:
            self._toggle_action.setText("Stop Recording" if recording else "Start Recording")
        self._apply_icon(recording)

    def set_recording_indicator(self, recording: bool):
        self._apply_icon(recording)

    def set_model(self, model: str):
        self._current_model = model
        for m, action in self._model_actions.items():
            action.setChecked(m == model)

    def set_device(self, device: str):
        self._current_device = device
        for d, action in self._device_actions.items():
            action.setChecked(d == device)

    def notify(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information, timeout: int = 2000):
        if self.tray:
            self.tray.showMessage(title, message, icon, timeout)
