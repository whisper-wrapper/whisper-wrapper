"""Settings dialog for Whisper GUI Wrapper."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSlider,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QProgressDialog,
)

from ..config import config, AVAILABLE_MODELS, get_display_server, OVERLAY_THEMES
from ..audio import list_devices
from ..model import is_model_cached, remove_model_cache, transcriber
from ..logging_utils import get_logger

logger = get_logger("settings")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Whisper Wrapper Settings")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        hotkey_group = QGroupBox("Hotkeys")
        hotkey_layout = QFormLayout(hotkey_group)

        self._toggle_hotkey = QLineEdit()
        self._toggle_hotkey.setPlaceholderText("<ctrl>+<alt>+r")
        hotkey_layout.addRow("Toggle Recording:", self._toggle_hotkey)

        self._cancel_hotkey = QLineEdit()
        self._cancel_hotkey.setPlaceholderText("escape")
        hotkey_layout.addRow("Cancel Recording:", self._cancel_hotkey)

        if get_display_server() != "x11":
            wayland_label = QLabel(
                "Note: On Wayland, use system shortcuts to run:\n"
                "whisper-trigger toggle"
            )
            wayland_label.setStyleSheet("color: #888; font-style: italic;")
            hotkey_layout.addRow(wayland_label)

        layout.addWidget(hotkey_group)

        audio_group = QGroupBox("Audio")
        audio_layout = QFormLayout(audio_group)

        self._microphone = QComboBox()
        self._microphone.addItem("Default", None)
        for dev in list_devices():
            self._microphone.addItem(dev['name'], dev['name'])
        audio_layout.addRow("Microphone:", self._microphone)

        self._vad_enabled = QCheckBox("Enable Voice Activity Detection")
        audio_layout.addRow(self._vad_enabled)

        self._vad_timeout_layout = QHBoxLayout()
        self._vad_timeout = QSlider(Qt.Orientation.Horizontal)
        self._vad_timeout.setRange(5, 30)  # 0.5 - 3.0 seconds * 10
        self._vad_timeout.setTickInterval(5)
        self._vad_timeout.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._vad_timeout_label = QLabel("1.5s")
        self._vad_timeout.valueChanged.connect(
            lambda v: self._vad_timeout_label.setText(f"{v/10:.1f}s")
        )
        self._vad_timeout_layout.addWidget(self._vad_timeout)
        self._vad_timeout_layout.addWidget(self._vad_timeout_label)
        audio_layout.addRow("Silence Timeout:", self._vad_timeout_layout)

        self._vad_threshold = QComboBox()
        self._vad_threshold.addItem("Low (more sensitive)", 1)
        self._vad_threshold.addItem("Medium", 2)
        self._vad_threshold.addItem("High (less sensitive)", 3)
        audio_layout.addRow("VAD Sensitivity:", self._vad_threshold)

        layout.addWidget(audio_group)

        model_group = QGroupBox("Transcription")
        model_layout = QFormLayout(model_group)

        self._model = QComboBox()
        for model in AVAILABLE_MODELS:
            self._model.addItem(model)
        model_layout.addRow("Model:", self._model)

        self._device = QComboBox()
        self._device.addItem("Auto (GPU if available)", "auto")
        self._device.addItem("CPU only", "cpu")
        self._device.addItem("GPU (CUDA)", "cuda")
        model_layout.addRow("Device:", self._device)

        self._language = QComboBox()
        self._language.addItem("Auto-detect", None)
        languages = [
            ("en", "English"), ("ru", "Russian"), ("de", "German"),
            ("fr", "French"), ("es", "Spanish"), ("it", "Italian"),
            ("pt", "Portuguese"), ("pl", "Polish"), ("uk", "Ukrainian"),
            ("ja", "Japanese"), ("ko", "Korean"), ("zh", "Chinese"),
        ]
        for code, name in languages:
            self._language.addItem(name, code)
        model_layout.addRow("Language:", self._language)

        self._auto_paste = QCheckBox("Auto paste result into active cursor")
        model_layout.addRow("", self._auto_paste)

        self._overlay_theme = QComboBox()
        for theme in OVERLAY_THEMES:
            self._overlay_theme.addItem(theme.title(), theme)
        model_layout.addRow("Overlay theme:", self._overlay_theme)

        self._overlay_opacity = QSlider(Qt.Orientation.Horizontal)
        self._overlay_opacity.setRange(10, 100)
        self._overlay_opacity_label = QLabel()
        self._overlay_opacity.valueChanged.connect(lambda v: self._overlay_opacity_label.setText(f"{v}%"))
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._overlay_opacity)
        opacity_row.addWidget(self._overlay_opacity_label)
        model_layout.addRow("Overlay opacity:", opacity_row)

        self._cache_status = QLabel(); self._cache_status.setStyleSheet("color: #888;")
        model_layout.addRow("Cache:", self._cache_status)

        cache_buttons = QHBoxLayout()
        self._download_model_btn = QPushButton("Download/Update"); self._download_model_btn.clicked.connect(self._download_selected_model); cache_buttons.addWidget(self._download_model_btn)
        self._clear_cache_btn = QPushButton("Delete Cache"); self._clear_cache_btn.clicked.connect(self._clear_selected_cache); cache_buttons.addWidget(self._clear_cache_btn)
        model_layout.addRow("", cache_buttons)
        self._model.currentIndexChanged.connect(lambda _: self._update_cache_status())

        layout.addWidget(model_group)

        button_layout = QHBoxLayout(); button_layout.addStretch()
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject); button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save"); save_btn.setDefault(True); save_btn.clicked.connect(self._save_settings); button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

    def _load_settings(self):
        settings = config.settings
        self._toggle_hotkey.setText(settings.hotkey_toggle)
        self._cancel_hotkey.setText(settings.hotkey_cancel)
        idx = self._microphone.findData(settings.microphone)
        if idx >= 0:
            self._microphone.setCurrentIndex(idx)
        self._vad_enabled.setChecked(settings.vad_enabled)
        self._vad_timeout.setValue(int(settings.vad_silence_timeout * 10))
        idx = self._vad_threshold.findData(settings.vad_threshold)
        if idx >= 0:
            self._vad_threshold.setCurrentIndex(idx)
        idx = self._model.findText(settings.model_size)
        if idx >= 0:
            self._model.setCurrentIndex(idx)
        idx = self._device.findData(settings.device)
        if idx >= 0:
            self._device.setCurrentIndex(idx)
        idx = self._language.findData(settings.language)
        if idx >= 0:
            self._language.setCurrentIndex(idx)
        self._auto_paste.setChecked(settings.auto_paste)
        idx = self._overlay_theme.findData(settings.overlay_theme)
        if idx >= 0:
            self._overlay_theme.setCurrentIndex(idx)
        self._overlay_opacity.setValue(int(settings.overlay_opacity * 100))
        self._overlay_opacity_label.setText(f"{int(settings.overlay_opacity*100)}%")
        self._update_cache_status()

    def _save_settings(self):
        try:
            config.update(
                hotkey_toggle=self._toggle_hotkey.text(),
                hotkey_cancel=self._cancel_hotkey.text(),
                microphone=self._microphone.currentData(),
                vad_enabled=self._vad_enabled.isChecked(),
                vad_silence_timeout=self._vad_timeout.value() / 10.0,
                vad_threshold=self._vad_threshold.currentData(),
                model_size=self._model.currentText(),
                device=self._device.currentData(),
                language=self._language.currentData(),
                auto_paste=self._auto_paste.isChecked(),
                overlay_theme=self._overlay_theme.currentData(),
                overlay_opacity=self._overlay_opacity.value() / 100.0,
            )

            logger.info("Settings saved")
            self.accept()

            QMessageBox.information(self, "Settings Saved", "Settings saved. Some changes may require restart.")

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _update_cache_status(self):
        model = self._model.currentText()
        cached = is_model_cached(model)
        status = "Cached" if cached else "Not cached"
        self._cache_status.setText(status)
        self._clear_cache_btn.setEnabled(cached)

    def _download_selected_model(self):
        model = self._model.currentText()
        progress = QProgressDialog(f"Downloading {model}...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        def on_progress(status: str, percent: float):
            progress.setLabelText(f"{status.capitalize()} {model}...")
            progress.setValue(int(percent))
            QApplication.processEvents()

        success = transcriber.load_model(model_name=model, progress_callback=on_progress, force_reload=True)
        progress.close()
        if success:
            self._update_cache_status()
            QMessageBox.information(self, "Model", f"{model} ready (cached)")
        else:
            QMessageBox.critical(self, "Model", f"Failed to download {model}")

    def _clear_selected_cache(self):
        model = self._model.currentText()
        if remove_model_cache(model):
            if transcriber.current_model == model:
                transcriber.unload_model()
            self._update_cache_status()
            QMessageBox.information(self, "Model Cache", f"Cache for {model} removed")
        else:
            QMessageBox.information(self, "Model Cache", f"No cache for {model}")
