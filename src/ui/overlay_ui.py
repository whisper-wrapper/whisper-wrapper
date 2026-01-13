"""UI setup for overlay widget."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QProgressBar,
    QTextEdit,
    QHBoxLayout,
    QPushButton,
    QCheckBox,
    QSizeGrip,
)


def setup_overlay_ui(widget: QWidget) -> dict:
    """Setup overlay UI and return widget references."""
    widget.setMinimumSize(420, 120)
    widget.setMaximumSize(940, 360)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(12, 10, 12, 2)
    layout.setSpacing(2)

    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
    label.setStyleSheet("color: white;")
    label.setWordWrap(True)
    layout.addWidget(label)

    status_detail = QLabel()
    status_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status_detail.setStyleSheet("color: rgba(255, 255, 255, 200);")
    layout.addWidget(status_detail)

    text_view = QTextEdit()
    text_view.setReadOnly(False)
    text_view.setMinimumHeight(140)
    text_view.setMaximumHeight(300)
    text_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    layout.addWidget(text_view)

    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setTextVisible(False)
    progress_bar.setFixedHeight(8)
    progress_bar.hide()
    layout.addWidget(progress_bar)

    level_bar = QProgressBar()
    level_bar.setRange(0, 100)
    level_bar.setTextVisible(False)
    level_bar.setFixedHeight(4)
    level_bar.hide()
    layout.addWidget(level_bar)

    stats_label = QLabel()
    stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(stats_label)

    actions = QHBoxLayout()
    record_btn = _make_action_button("Record")
    copy_btn = _make_action_button("Copy")
    paste_btn = _make_action_button("Paste")
    hide_btn = _make_action_button("Hide")
    actions.addStretch()
    actions.addWidget(record_btn)
    actions.addWidget(copy_btn)
    actions.addWidget(paste_btn)
    actions.addWidget(hide_btn)

    auto_paste_box = QCheckBox("Auto paste")
    auto_paste_box.setChecked(True)
    actions.addWidget(auto_paste_box)
    actions.addStretch()

    actions_container = QWidget()
    actions_container.setLayout(actions)
    actions_container.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(actions_container)

    grip_row = QHBoxLayout()
    grip_row.setContentsMargins(0, 0, 0, 0)
    grip_row.setSpacing(0)
    grip_row.addStretch()
    grip = QSizeGrip(widget)
    grip.setFixedSize(12, 12)
    grip_row.addWidget(grip)
    grip_container = QWidget()
    grip_container.setLayout(grip_row)
    layout.addWidget(grip_container)

    return {
        "label": label,
        "status_detail": status_detail,
        "text_view": text_view,
        "progress_bar": progress_bar,
        "level_bar": level_bar,
        "stats_label": stats_label,
        "record_btn": record_btn,
        "copy_btn": copy_btn,
        "paste_btn": paste_btn,
        "hide_btn": hide_btn,
        "auto_paste_box": auto_paste_box,
    }


def _make_action_button(label: str) -> QPushButton:
    btn = QPushButton(label)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setFlat(True)
    return btn
