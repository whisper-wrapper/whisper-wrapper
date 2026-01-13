"""UI group builders for settings dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSlider,
    QPushButton,
    QGroupBox,
    QHBoxLayout,
)

from ..config import AVAILABLE_MODELS, get_display_server, OVERLAY_THEMES
from ..audio import list_devices

LANGUAGES = [
    ("en", "English"),
    ("ru", "Russian"),
    ("de", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("pl", "Polish"),
    ("uk", "Ukrainian"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("zh", "Chinese"),
]


def build_hotkey_group():
    """Build hotkey settings group."""
    group = QGroupBox("Hotkeys")
    layout = QFormLayout(group)

    toggle_hotkey = QLineEdit()
    toggle_hotkey.setPlaceholderText("<ctrl>+<alt>+r")
    layout.addRow("Toggle Recording:", toggle_hotkey)

    cancel_hotkey = QLineEdit()
    cancel_hotkey.setPlaceholderText("escape")
    layout.addRow("Cancel Recording:", cancel_hotkey)

    if get_display_server() != "x11":
        label = QLabel(
            "Note: On Wayland, use system shortcuts to run:\nwhisper-trigger toggle"
        )
        label.setStyleSheet("color: #888; font-style: italic;")
        layout.addRow(label)

    return group, {"toggle": toggle_hotkey, "cancel": cancel_hotkey}


def build_audio_group():
    """Build audio settings group."""
    group = QGroupBox("Audio")
    layout = QFormLayout(group)

    microphone = QComboBox()
    microphone.addItem("Default", None)
    for dev in list_devices():
        microphone.addItem(dev["name"], dev["name"])
    layout.addRow("Microphone:", microphone)

    vad_enabled = QCheckBox("Enable Voice Activity Detection")
    layout.addRow(vad_enabled)

    vad_timeout = QSlider(Qt.Orientation.Horizontal)
    vad_timeout.setRange(5, 30)
    vad_timeout.setTickInterval(5)
    vad_timeout.setTickPosition(QSlider.TickPosition.TicksBelow)
    vad_timeout_label = QLabel("1.5s")
    vad_timeout.valueChanged.connect(
        lambda v: vad_timeout_label.setText(f"{v/10:.1f}s")
    )
    timeout_layout = QHBoxLayout()
    timeout_layout.addWidget(vad_timeout)
    timeout_layout.addWidget(vad_timeout_label)
    layout.addRow("Silence Timeout:", timeout_layout)

    vad_threshold = QComboBox()
    vad_threshold.addItem("Low (more sensitive)", 1)
    vad_threshold.addItem("Medium", 2)
    vad_threshold.addItem("High (less sensitive)", 3)
    layout.addRow("VAD Sensitivity:", vad_threshold)

    return group, {
        "microphone": microphone,
        "vad_enabled": vad_enabled,
        "vad_timeout": vad_timeout,
        "vad_timeout_label": vad_timeout_label,
        "vad_threshold": vad_threshold,
    }


def build_model_group():
    """Build transcription/model settings group."""
    group = QGroupBox("Transcription")
    layout = QFormLayout(group)

    model = QComboBox()
    for m in AVAILABLE_MODELS:
        model.addItem(m)
    layout.addRow("Model:", model)

    device = QComboBox()
    device.addItem("Auto (GPU if available)", "auto")
    device.addItem("CPU only", "cpu")
    device.addItem("GPU (CUDA)", "cuda")
    layout.addRow("Device:", device)

    language = QComboBox()
    language.addItem("Auto-detect", None)
    for code, name in LANGUAGES:
        language.addItem(name, code)
    layout.addRow("Language:", language)

    auto_paste = QCheckBox("Auto paste result into active cursor")
    layout.addRow("", auto_paste)

    overlay_theme = QComboBox()
    for theme in OVERLAY_THEMES:
        overlay_theme.addItem(theme.title(), theme)
    layout.addRow("Overlay theme:", overlay_theme)

    overlay_opacity = QSlider(Qt.Orientation.Horizontal)
    overlay_opacity.setRange(10, 100)
    opacity_label = QLabel()
    overlay_opacity.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
    opacity_row = QHBoxLayout()
    opacity_row.addWidget(overlay_opacity)
    opacity_row.addWidget(opacity_label)
    layout.addRow("Overlay opacity:", opacity_row)

    cache_status = QLabel()
    cache_status.setStyleSheet("color: #888;")
    layout.addRow("Cache:", cache_status)

    cache_buttons = QHBoxLayout()
    download_btn = QPushButton("Download/Update")
    clear_btn = QPushButton("Delete Cache")
    cache_buttons.addWidget(download_btn)
    cache_buttons.addWidget(clear_btn)
    layout.addRow("", cache_buttons)

    return group, {
        "model": model,
        "device": device,
        "language": language,
        "auto_paste": auto_paste,
        "overlay_theme": overlay_theme,
        "overlay_opacity": overlay_opacity,
        "opacity_label": opacity_label,
        "cache_status": cache_status,
        "download_btn": download_btn,
        "clear_btn": clear_btn,
    }
