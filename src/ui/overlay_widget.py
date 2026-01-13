"""Overlay widget showing status and progress."""

from typing import Optional, Callable
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QBrush
from PyQt6.QtWidgets import QWidget, QApplication
from ..logging_utils import get_logger
from .icons import make_record_icon
from .themes import get_overlay_palette
from .overlay_state import OverlayState, STATE_LABELS
from .overlay_ui import setup_overlay_ui

logger = get_logger("ui.overlay")


class StatusOverlay(QWidget):
    state_changed = pyqtSignal(OverlayState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = OverlayState.HIDDEN
        self._progress: float = 0
        self._audio_level: float = 0
        self._opacity: float = 0.7
        self._on_copy: Optional[Callable[[], None]] = None
        self._on_paste: Optional[Callable[[], None]] = None
        self._on_hide: Optional[Callable[[], None]] = None
        self._on_auto_paste_change: Optional[Callable[[bool], None]] = None
        self._on_toggle: Optional[Callable[[], None]] = None
        self._is_recording: bool = False
        self._drag_pos = None
        self._user_positioned = False
        self._setup_ui()
        self.set_theme("dark")
        self._setup_window()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(self._opacity)
        self._reposition()

    def _setup_ui(self):
        widgets = setup_overlay_ui(self)
        self._label = widgets["label"]
        self._status_detail = widgets["status_detail"]
        self._text_view = widgets["text_view"]
        self._progress_bar = widgets["progress_bar"]
        self._level_bar = widgets["level_bar"]
        self._stats_label = widgets["stats_label"]
        self._record_btn = widgets["record_btn"]
        self._copy_btn = widgets["copy_btn"]
        self._paste_btn = widgets["paste_btn"]
        self._hide_btn = widgets["hide_btn"]
        self._auto_paste_box = widgets["auto_paste_box"]

        self._record_btn.clicked.connect(lambda: self._on_toggle and self._on_toggle())
        self._copy_btn.clicked.connect(lambda: self._on_copy and self._on_copy())
        self._paste_btn.clicked.connect(lambda: self._on_paste and self._on_paste())
        self._hide_btn.clicked.connect(lambda: self._on_hide and self._on_hide())
        self._auto_paste_box.stateChanged.connect(
            lambda s: self._on_auto_paste_change
            and self._on_auto_paste_change(s == Qt.CheckState.Checked)
        )

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.right() - self.width() - 20, geo.bottom() - self.height() - 20
            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def set_theme(self, theme: str):
        if theme not in ("dark", "light"):
            theme = "dark"
        c = get_overlay_palette(theme)
        self._colors, self._bg_color = c, c["bg"]
        self._label.setStyleSheet(f"color: {c['text']};")
        self._status_detail.setStyleSheet(f"color: {c['muted']}; font-size: 11px;")
        self._text_view.setStyleSheet(
            f"QTextEdit {{ background: transparent; color: {c['text']}; border: none; }}"
        )
        self._progress_bar.setStyleSheet(
            f"QProgressBar{{background-color:{c['bar_bg']};border-radius:4px;}}"
            f"QProgressBar::chunk{{background-color:{c['accent']};border-radius:4px;}}"
        )
        self._level_bar.setStyleSheet(
            f"QProgressBar{{background-color:{c['level_bg']};border-radius:2px;}}"
            f"QProgressBar::chunk{{background-color:{c['accent']};border-radius:2px;}}"
        )
        self._stats_label.setStyleSheet(f"color: {c['muted']}; font-size: 10px;")
        btn_style = (
            f"QPushButton{{color:{c['text']};background:transparent;border:1px solid {c['bar_bg']};"
            f"border-radius:6px;padding:4px 10px;}}QPushButton:hover{{background:{c['bar_bg']};}}"
        )
        for btn in (self._copy_btn, self._paste_btn, self._hide_btn):
            btn.setStyleSheet(btn_style)
        self._auto_paste_box.setStyleSheet(f"color:{c['text']};")
        self.set_recording_state(self._is_recording)
        self.update()

    def set_state(self, state: OverlayState, message: Optional[str] = None):
        self._state = state
        self._label.setText(message or STATE_LABELS.get(state, ""))
        self._progress_bar.setVisible(state == OverlayState.DOWNLOADING)
        self._level_bar.setVisible(state == OverlayState.RECORDING)
        self._text_view.setVisible(True)
        if state == OverlayState.HIDDEN:
            self.hide()
        else:
            self.show()
            if not self._user_positioned:
                self._reposition()
        self.update()
        self.state_changed.emit(state)

    def set_progress(self, progress: float):
        self._progress_bar.setValue(int(max(0, min(100, progress))))

    def set_audio_level(self, level: float):
        self._level_bar.setValue(min(100, int(max(0, min(1, level)) * 500)))

    def show_temporary(
        self,
        state: OverlayState,
        message: Optional[str] = None,
        duration_ms: int = 2000,
    ):
        self.set_state(state, message)
        QTimer.singleShot(duration_ms, lambda: self.set_state(OverlayState.IDLE))

    def set_text(self, text: str):
        self._text_view.setPlainText(text)
        self._text_view.verticalScrollBar().setValue(
            self._text_view.verticalScrollBar().maximum()
        )
        self.adjustSize()
        if not self._user_positioned:
            self._reposition()

    def set_hints(self, hints: str):
        pass

    def set_opacity(self, opacity: float):
        self._opacity = max(0.1, min(1.0, opacity))
        self.setWindowOpacity(self._opacity)

    def set_status_detail(self, detail: str):
        self._status_detail.setText(detail)

    def set_stats(self, stats: str):
        self._stats_label.setText(stats)

    def set_actions(
        self,
        on_copy=None,
        on_paste=None,
        on_hide=None,
        on_auto_paste_change=None,
        on_toggle=None,
    ):
        self._on_copy, self._on_paste, self._on_hide = on_copy, on_paste, on_hide
        self._on_auto_paste_change, self._on_toggle = on_auto_paste_change, on_toggle

    def set_auto_paste(self, enabled: bool):
        self._auto_paste_box.blockSignals(True)
        self._auto_paste_box.setChecked(bool(enabled))
        self._auto_paste_box.blockSignals(False)

    def set_recording_state(self, recording: bool):
        self._is_recording = recording
        self._record_btn.setText("Stop" if recording else "Record")
        base = "#b71c1c" if recording else "#e53935"
        style = (
            f"QPushButton{{color:{'#fff' if recording else base};background:{base if recording else 'rgba(229,57,53,0.12)'};"
            f"border:1px solid {base};border-radius:6px;padding:6px 14px;font-weight:600;}}"
            f"QPushButton:hover{{background:{'#c62828' if recording else '#e53935'};color:#fff;}}"
        )
        self._record_btn.setStyleSheet(style)
        self._record_btn.setIcon(make_record_icon(base))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self._user_positioned = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        self._user_positioned = True
        super().resizeEvent(event)

    def hide_overlay(self):
        self._state = OverlayState.HIDDEN
        self.hide()

    @property
    def state(self) -> OverlayState:
        return self._state
