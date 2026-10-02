from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSlider,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QProgressBar,
    QWidget,
    QMessageBox,
)
from ..config.settings import settings
from ..audio.voice_manager import voice_manager
from ..audio.tts_engine import tts_engine
from .styles import DIALOG_STYLE, COLORS


class SettingsDialog(QDialog):
    """Modern Windows 11 Fluent settings dialog for voice, audio, and shortcuts."""

    settings_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ReadAloud Desktop AI - Settings")
        self.setMinimumSize(560, 690)
        self.resize(560, 720)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        title_label = QLabel("ReadAloud Desktop AI")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)

        sub_label = QLabel("Control your 100% local, natural neural speech anywhere in Windows 11")
        sub_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(sub_label)

        # --- Section 1: Voice & Speech ---
        voice_group = QGroupBox("Neural AI Voice")
        v_layout = QVBoxLayout(voice_group)
        v_layout.setContentsMargins(16, 22, 16, 18)
        v_layout.setSpacing(14)

        # Voice selector + Preview button in one clean row
        v_select_layout = QHBoxLayout()
        v_select_layout.setSpacing(10)
        v_label = QLabel("Voice:")
        self.voice_combo = QComboBox()
        for v in voice_manager.get_voices():
            self.voice_combo.addItem(v.display_name, v.id)

        self.preview_btn = QPushButton("🔊 Preview")
        self.preview_btn.setToolTip("Play a sample of this voice")
        self.preview_btn.setFixedWidth(110)
        self.preview_btn.clicked.connect(self._preview_voice)

        v_select_layout.addWidget(v_label)
        v_select_layout.addWidget(self.voice_combo, stretch=1)
        v_select_layout.addWidget(self.preview_btn)
        v_layout.addLayout(v_select_layout)

        # Speed slider
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Speed:")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 25)  # 0.5x to 2.5x
        self.speed_slider.setValue(10)
        self.speed_value_label = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(
            lambda val: self.speed_value_label.setText(f"{val / 10:.1f}x")
        )
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider, stretch=1)
        speed_layout.addWidget(self.speed_value_label)
        v_layout.addLayout(speed_layout)

        # Volume slider
        vol_layout = QHBoxLayout()
        vol_label = QLabel("Volume:")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_value_label = QLabel("100%")
        self.vol_slider.valueChanged.connect(
            lambda val: self.vol_value_label.setText(f"{val}%")
        )
        vol_layout.addWidget(vol_label)
        vol_layout.addWidget(self.vol_slider, stretch=1)
        vol_layout.addWidget(self.vol_value_label)
        v_layout.addLayout(vol_layout)

        layout.addWidget(voice_group)

        # --- Section 2: Shortcuts & Controls ---
        hotkey_group = QGroupBox("Global Hotkeys")
        h_layout = QVBoxLayout(hotkey_group)
        h_layout.setContentsMargins(16, 20, 16, 16)
        h_layout.setSpacing(8)

        h1 = QLabel("<b>Ctrl + Alt + R</b>  —  Read selected text anywhere")
        h2 = QLabel("<b>Ctrl + Alt + S</b>  —  Snip & read any screen area (OCR)")
        h3 = QLabel("<b>Click Floating Circle</b>  —  Read selected text or Pause/Resume")
        for h in [h1, h2, h3]:
            h.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 2px 0;")
            h_layout.addWidget(h)

        layout.addWidget(hotkey_group)

        # --- Section 3: System Options ---
        sys_group = QGroupBox("Windows Behavior")
        s_layout = QVBoxLayout(sys_group)
        s_layout.setContentsMargins(16, 20, 16, 16)
        s_layout.setSpacing(10)

        self.startup_check = QCheckBox("Start ReadAloud with Windows 11")
        self.circle_check = QCheckBox("Show floating circle widget on screen")
        self.clipboard_check = QCheckBox("Automatically read text when copied (Ctrl+C)")
        self.popover_check = QCheckBox("Show quick-read button (🔊 Read) near highlighted text")

        s_layout.addWidget(self.startup_check)
        s_layout.addWidget(self.circle_check)
        s_layout.addWidget(self.clipboard_check)
        s_layout.addWidget(self.popover_check)

        layout.addWidget(sys_group)

        # Status & Progress
        self.status_label = QLabel(
            "Local AI Status: " + ("Ready (100% Offline)" if voice_manager.is_ready() else "Models downloading...")
        )
        self.status_label.setStyleSheet(f"color: {COLORS['state_playing'] if voice_manager.is_ready() else COLORS['state_paused']}; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save && Apply")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_and_close)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        # Voice
        idx = self.voice_combo.findData(settings.voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)

        # Speed
        speed_int = int(settings.speed * 10)
        self.speed_slider.setValue(speed_int)
        self.speed_value_label.setText(f"{settings.speed:.1f}x")

        # Volume
        vol_int = int(settings.volume * 100)
        self.vol_slider.setValue(vol_int)
        self.vol_value_label.setText(f"{vol_int}%")

        # Checkboxes
        self.startup_check.setChecked(settings.start_with_windows)
        self.circle_check.setChecked(settings.get("circle_visible", True))
        self.clipboard_check.setChecked(settings.get("auto_read_clipboard", False))
        self.popover_check.setChecked(settings.get("show_selection_popover", True))

    def _preview_voice(self):
        voice_id = self.voice_combo.currentData()
        speed = self.speed_slider.value() / 10.0
        tts_engine.speak(
            "Hello! This is a natural local AI voice reading aloud on your desktop.",
            voice=voice_id,
            speed=speed,
        )

    def _save_and_close(self):
        # Save settings
        settings.voice = self.voice_combo.currentData()
        settings.speed = self.speed_slider.value() / 10.0
        settings.volume = self.vol_slider.value() / 100.0
        settings.start_with_windows = self.startup_check.isChecked()
        settings.set("circle_visible", self.circle_check.isChecked())
        settings.set("auto_read_clipboard", self.clipboard_check.isChecked())
        settings.set("show_selection_popover", self.popover_check.isChecked())

        self.settings_updated.emit()
        self.accept()

