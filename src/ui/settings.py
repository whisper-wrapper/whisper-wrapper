"""Settings dialog for Whisper GUI Wrapper."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QProgressDialog,
)

from ..config import config
from ..model import is_model_cached, remove_model_cache, transcriber
from ..logging_utils import get_logger
from .settings_groups import build_hotkey_group, build_audio_group, build_model_group

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

        hotkey_group, hotkey_widgets = build_hotkey_group()
        self._toggle_hotkey = hotkey_widgets["toggle"]
        self._cancel_hotkey = hotkey_widgets["cancel"]
        layout.addWidget(hotkey_group)

        audio_group, audio_widgets = build_audio_group()
        self._microphone = audio_widgets["microphone"]
        self._vad_enabled = audio_widgets["vad_enabled"]
        self._vad_timeout = audio_widgets["vad_timeout"]
        self._vad_timeout_label = audio_widgets["vad_timeout_label"]
        self._vad_threshold = audio_widgets["vad_threshold"]
        layout.addWidget(audio_group)

        model_group, model_widgets = build_model_group()
        self._model = model_widgets["model"]
        self._device = model_widgets["device"]
        self._language = model_widgets["language"]
        self._auto_paste = model_widgets["auto_paste"]
        self._overlay_theme = model_widgets["overlay_theme"]
        self._overlay_opacity = model_widgets["overlay_opacity"]
        self._overlay_opacity_label = model_widgets["opacity_label"]
        self._cache_status = model_widgets["cache_status"]
        self._download_model_btn = model_widgets["download_btn"]
        self._clear_cache_btn = model_widgets["clear_btn"]
        self._download_model_btn.clicked.connect(self._download_selected_model)
        self._clear_cache_btn.clicked.connect(self._clear_selected_cache)
        self._model.currentIndexChanged.connect(lambda _: self._update_cache_status())
        layout.addWidget(model_group)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

    def _load_settings(self):
        s = config.settings
        self._toggle_hotkey.setText(s.hotkey_toggle)
        self._cancel_hotkey.setText(s.hotkey_cancel)
        self._set_combo_by_data(self._microphone, s.microphone)
        self._vad_enabled.setChecked(s.vad_enabled)
        self._vad_timeout.setValue(int(s.vad_silence_timeout * 10))
        self._set_combo_by_data(self._vad_threshold, s.vad_threshold)
        self._set_combo_by_text(self._model, s.model_size)
        self._set_combo_by_data(self._device, s.device)
        self._set_combo_by_data(self._language, s.language)
        self._auto_paste.setChecked(s.auto_paste)
        self._set_combo_by_data(self._overlay_theme, s.overlay_theme)
        self._overlay_opacity.setValue(int(s.overlay_opacity * 100))
        self._overlay_opacity_label.setText(f"{int(s.overlay_opacity * 100)}%")
        self._update_cache_status()

    def _set_combo_by_data(self, combo, value):
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_combo_by_text(self, combo, value):
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

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
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings saved. Some changes may require restart.",
            )
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _update_cache_status(self):
        model = self._model.currentText()
        cached = is_model_cached(model)
        self._cache_status.setText("Cached" if cached else "Not cached")
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

        success = transcriber.load_model(
            model_name=model, progress_callback=on_progress, force_reload=True
        )
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
