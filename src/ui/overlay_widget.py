"""Overlay widget showing status and progress."""
from typing import Optional, Callable
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QFont, QCursor
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QProgressBar, QTextEdit, QHBoxLayout, QPushButton, QCheckBox, QSizeGrip
from ..logging_utils import get_logger
from .icons import make_record_icon
from .themes import get_overlay_palette
from .overlay_state import OverlayState, STATE_LABELS
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
        self.setMinimumSize(420, 120)
        self.setMaximumSize(940, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 2)
        layout.setSpacing(2)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        self._label.setStyleSheet("color: white;")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        self._status_detail = QLabel()
        self._status_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_detail.setStyleSheet("color: rgba(255, 255, 255, 200);")
        layout.addWidget(self._status_detail)
        self._text_view = QTextEdit()
        self._text_view.setReadOnly(False)
        self._text_view.setMinimumHeight(140)
        self._text_view.setMaximumHeight(300)
        self._text_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._text_view)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)
        self._level_bar = QProgressBar()
        self._level_bar.setRange(0, 100)
        self._level_bar.setTextVisible(False)
        self._level_bar.setFixedHeight(4)
        self._level_bar.hide()
        layout.addWidget(self._level_bar)
        self._stats_label = QLabel()
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._stats_label)
        actions = QHBoxLayout()
        self._record_btn = self._make_action_button("Record", lambda: self._on_toggle and self._on_toggle())
        self._copy_btn = self._make_action_button("Copy", lambda: self._on_copy and self._on_copy())
        self._paste_btn = self._make_action_button("Paste", lambda: self._on_paste and self._on_paste())
        self._hide_btn = self._make_action_button("Hide", lambda: self._on_hide and self._on_hide())
        actions.addStretch()
        actions.addWidget(self._record_btn)
        actions.addWidget(self._copy_btn)
        actions.addWidget(self._paste_btn)
        actions.addWidget(self._hide_btn)
        self._auto_paste_box = QCheckBox("Auto paste")
        self._auto_paste_box.setChecked(True)
        self._auto_paste_box.stateChanged.connect(
            lambda s: self._on_auto_paste_change and self._on_auto_paste_change(s == Qt.CheckState.Checked)
        )
        actions.addWidget(self._auto_paste_box)
        actions.addStretch()
        actions_container = QWidget()
        actions_container.setLayout(actions)
        actions_container.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(actions_container)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.setSpacing(0)
        grip_row.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(12, 12)
        grip_row.addWidget(grip)
        grip_container = QWidget()
        grip_container.setLayout(grip_row)
        layout.addWidget(grip_container)
    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 20
            y = geometry.bottom() - self.height() - 20
            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def set_theme(self, theme: str):
        """Apply light/dark theme."""
        if theme not in ("dark", "light"):
            theme = "dark"
        self._colors = get_overlay_palette(theme)
        self._bg_color = self._colors["bg"]
        self._label.setStyleSheet(f"color: {self._colors['text']};")
        self._status_detail.setStyleSheet(f"color: {self._colors['muted']}; font-size: 11px;")
        self._text_view.setStyleSheet(f"QTextEdit {{ background: transparent; color: {self._colors['text']}; border: none; }}")
        self._progress_bar.setStyleSheet(
            f"QProgressBar{{background-color:{self._colors['bar_bg']};border-radius:4px;}}"
            f"QProgressBar::chunk{{background-color:{self._colors['accent']};border-radius:4px;}}"
        )
        self._level_bar.setStyleSheet(
            f"QProgressBar{{background-color:{self._colors['level_bg']};border-radius:2px;}}"
            f"QProgressBar::chunk{{background-color:{self._colors['accent']};border-radius:2px;}}"
        )
        self._stats_label.setStyleSheet(f"color: {self._colors['muted']}; font-size: 10px;")
        btn_style = (
            f"QPushButton{{color:{self._colors['text']};background:transparent;border:1px solid {self._colors['bar_bg']};"
            f"border-radius:6px;padding:4px 10px;}}QPushButton:hover{{background:{self._colors['bar_bg']};}}"
        )
        for btn in (self._copy_btn, self._paste_btn, self._hide_btn):
            btn.setStyleSheet(btn_style)
        self._auto_paste_box.setStyleSheet(f"color:{self._colors['text']};")
        self.set_recording_state(self._is_recording)
        self.update()

    def set_state(self, state: OverlayState, message: Optional[str] = None):
        self._state = state
        label_text = message or STATE_LABELS.get(state, "")
        self._label.setText(label_text)
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
        self._progress = max(0, min(100, progress))
        self._progress_bar.setValue(int(self._progress))

    def set_audio_level(self, level: float):
        self._audio_level = max(0, min(1, level))
        scaled = min(100, int(self._audio_level * 500))
        self._level_bar.setValue(scaled)
    def show_temporary(self, state: OverlayState, message: Optional[str] = None, duration_ms: int = 2000):
        self.set_state(state, message); QTimer.singleShot(duration_ms, lambda: self.set_state(OverlayState.IDLE))

    def set_text(self, text: str):
        self._text_view.setPlainText(text)
        self._text_view.verticalScrollBar().setValue(self._text_view.verticalScrollBar().maximum())
        self.adjustSize()
        if not self._user_positioned:
            self._reposition()

    def set_hints(self, hints: str): pass
    def set_opacity(self, opacity: float): self._opacity = max(0.1, min(1.0, opacity)); self.setWindowOpacity(self._opacity)
    def set_status_detail(self, detail: str): self._status_detail.setText(detail)
    def set_stats(self, stats: str): self._stats_label.setText(stats)
    def set_actions(
        self,
        on_copy: Optional[Callable[[], None]] = None,
        on_paste: Optional[Callable[[], None]] = None,
        on_hide: Optional[Callable[[], None]] = None,
        on_auto_paste_change: Optional[Callable[[bool], None]] = None,
        on_toggle: Optional[Callable[[], None]] = None,
    ):
        self._on_copy = on_copy
        self._on_paste = on_paste
        self._on_hide = on_hide
        self._on_auto_paste_change = on_auto_paste_change
        self._on_toggle = on_toggle

    def set_auto_paste(self, enabled: bool):
        self._auto_paste_box.blockSignals(True); self._auto_paste_box.setChecked(bool(enabled)); self._auto_paste_box.blockSignals(False)

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

    def _make_action_button(self, label: str, handler: Callable[[], None]) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFlat(True)
        btn.clicked.connect(handler)
        return btn

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._user_positioned = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
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
