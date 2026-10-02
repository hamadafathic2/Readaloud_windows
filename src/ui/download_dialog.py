import threading
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QHBoxLayout,
)
from ..audio.voice_manager import voice_manager
from .styles import DIALOG_STYLE, COLORS


class DownloadDialog(QDialog):
    """Modern progress dialog shown on first launch while downloading local neural AI models."""

    progress_signal = pyqtSignal(str, int, int)
    completed_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ReadAloud AI - First Time Setup")
        self.setFixedSize(460, 200)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        self._build_ui()
        self.progress_signal.connect(self._update_progress)
        self.completed_signal.connect(self._on_finished)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Setting Up Local AI Neural Voice")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.status_label = QLabel("Preparing 100% offline voice engine...")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent_gradient_start']}, stop:1 {COLORS['accent_gradient_end']});
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self.bytes_label = QLabel("Once downloaded, works completely offline with zero internet.")
        self.bytes_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.bytes_label)

    def start_download(self):
        def _worker():
            def _callback(label, current, total):
                self.progress_signal.emit(label, current, total)

            success = voice_manager.ensure_models(progress_callback=_callback)
            self.completed_signal.emit(success)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _update_progress(self, label: str, current: int, total: int):
        self.status_label.setText(label)
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
            cur_mb = current / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.bytes_label.setText(f"{cur_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%)")

    def _on_finished(self, success: bool):
        if success:
            self.accept()
        else:
            self.status_label.setText("Download failed. Windows SAPI voice fallback will be used.")
            self.status_label.setStyleSheet("color: #ef4444;")
            # Accept after 2 seconds to let user continue
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self.accept)
