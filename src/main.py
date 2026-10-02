import sys
import os
import ctypes
from pathlib import Path

# Ensure project root is in sys.path
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)

from src.config.settings import settings
from src.audio.voice_manager import voice_manager
from src.audio.player import player
from src.audio.tts_engine import tts_engine
from src.capture.hotkeys import hotkey_manager
from src.ui.floating_circle import FloatingCircleWidget
from src.ui.snip_overlay import SnipOverlay
from src.ui.settings_dialog import SettingsDialog
from src.ui.download_dialog import DownloadDialog
from src.ui.selection_popover import SelectionPopover


MUTEX_NAME = "Global\\ReadAloudDesktopAI_SingleInstance_Mutex"


def acquire_single_instance_mutex():
    """Ensure only one instance of ReadAloud AI runs concurrently on Windows."""
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return None
    return mutex


class HotkeyBridge(QObject):
    sig_read = pyqtSignal()
    sig_snip = pyqtSignal()


class ReadAloudApp:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        ico_path = PROJECT_ROOT / "assets" / "icon.ico"
        png_path = PROJECT_ROOT / "assets" / "icon.png"
        self.app_icon = QIcon()
        if ico_path.exists():
            self.app_icon.addFile(str(ico_path))
        if png_path.exists():
            self.app_icon.addFile(str(png_path))
        self.icon_path = str(png_path if png_path.exists() else ico_path)
        self.qapp.setWindowIcon(self.app_icon)

        # Initialize Core UI
        self.circle_widget = FloatingCircleWidget()
        self.snip_overlay = SnipOverlay()
        self.settings_dialog = SettingsDialog()
        self.selection_popover = SelectionPopover()

        # Connect signals
        self.circle_widget.request_snip.connect(self._start_snip_safely)
        self.circle_widget.request_settings.connect(self._show_settings)
        self.circle_widget.request_hide.connect(self._hide_circle)
        self.circle_widget.request_close.connect(self._exit_app)
        self.circle_widget.clipboard_toggle_changed.connect(self._on_clipboard_toggle)
        self.snip_overlay.snip_no_text.connect(self._on_snip_no_text)
        self.settings_dialog.settings_updated.connect(self._on_settings_updated)
        self.selection_popover.request_read.connect(tts_engine.speak)

        # Thread-safe Hotkey Bridge
        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.sig_read.connect(self.circle_widget.read_selected_text)
        self.hotkey_bridge.sig_snip.connect(self._start_snip_safely)

        # Clipboard Watcher for Copy-to-Read (Ctrl+C)
        self._last_spoken_clipboard = ""
        self._init_clipboard_watcher()

        # System Tray
        self._init_tray()

        # Global Hotkeys
        self._init_hotkeys()

        # Check for first-time model setup
        self._check_models_on_startup()

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self.app_icon, self.qapp)
        self.tray.setToolTip("ReadAloud Desktop AI - Local Neural Speech")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #141821;
                color: #ffffff;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
        """)

        read_action = tray_menu.addAction("🔊 Read Selected Text (Ctrl+Alt+R)")
        read_action.triggered.connect(self.circle_widget.read_selected_text)

        snip_action = tray_menu.addAction("✂ Snip & Read (Ctrl+Alt+S)")
        snip_action.triggered.connect(self._start_snip_safely)

        tray_menu.addSeparator()

        self.toggle_circle_action = tray_menu.addAction("👁 Toggle Floating Circle")
        self.toggle_circle_action.triggered.connect(self._toggle_circle)

        self.auto_read_action = tray_menu.addAction("📋 Auto-Read Copied Text (Ctrl+C)")
        self.auto_read_action.setCheckable(True)
        self.auto_read_action.setChecked(settings.get("auto_read_clipboard", False))
        self.auto_read_action.toggled.connect(self._on_clipboard_toggle)

        pause_resume_action = tray_menu.addAction("⏯ Pause / Resume")
        pause_resume_action.triggered.connect(player.toggle_play_pause)

        stop_action = tray_menu.addAction("⏹ Stop Reading")
        stop_action.triggered.connect(tts_engine.stop)

        tray_menu.addSeparator()

        settings_action = tray_menu.addAction("⚙ Settings")
        settings_action.triggered.connect(self._show_settings)

        exit_action = tray_menu.addAction("❌ Exit ReadAloud")
        exit_action.triggered.connect(self._exit_app)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _init_clipboard_watcher(self):
        self.clipboard = self.qapp.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)

    def _on_clipboard_changed(self):
        if not settings.get("auto_read_clipboard", False):
            return

        text = self.clipboard.text()
        if not text:
            return

        clean = text.strip()
        if len(clean) < 2 or clean == self._last_spoken_clipboard:
            return

        self._last_spoken_clipboard = clean
        print(f"[ClipboardWatcher] Auto-reading {len(clean)} copied chars: {clean[:50]}...")
        tts_engine.speak(clean)

    def _on_clipboard_toggle(self, enabled: bool):
        settings.set("auto_read_clipboard", enabled)
        if hasattr(self, "auto_read_action") and self.auto_read_action.isChecked() != enabled:
            self.auto_read_action.setChecked(enabled)
        status_text = (
            "Auto-Read Copied Text ENABLED.\nSimply select text and press Ctrl+C to read it aloud!"
            if enabled
            else "Auto-Read Copied Text DISABLED."
        )
        self.tray.showMessage(
            "ReadAloud AI",
            status_text,
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _init_hotkeys(self):
        hotkey_manager.on_read_selection = self.hotkey_bridge.sig_read.emit
        hotkey_manager.on_snip_read = self.hotkey_bridge.sig_snip.emit
        hotkey_manager.start()

    def _check_models_on_startup(self):
        if not voice_manager.is_ready():
            # Show download dialog
            dl_dialog = DownloadDialog()
            dl_dialog.start_download()
            dl_dialog.exec()

        # Show circle if enabled
        if settings.get("circle_visible", True):
            self.circle_widget.show()

    def _start_snip_safely(self):
        was_visible = self.circle_widget.isVisible()
        if was_visible:
            self.circle_widget.hide()
            self.qapp.processEvents()

        def restore_circle():
            try:
                self.snip_overlay.snip_finished.disconnect(restore_circle)
            except Exception:
                pass
            if was_visible and settings.get("circle_visible", True):
                self.circle_widget.show()

        self.snip_overlay.snip_finished.connect(restore_circle)
        # Allow Windows DWM to finish repainting desktop before capturing screen
        QTimer.singleShot(60, self.snip_overlay.start_snip)

    def _show_settings(self):
        # Reload values so they reflect any changes made via the floating circle
        self.settings_dialog._load_values()
        self.settings_dialog.show()
        self.settings_dialog.activateWindow()

    def _on_snip_no_text(self):
        self.tray.showMessage(
            "ReadAloud AI",
            "No text detected in selected area. Try snipping with a bit more surrounding margin.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _hide_circle(self):
        self.circle_widget.hide()
        self.tray.showMessage(
            "ReadAloud AI",
            "Floating circle hidden. Click the tray icon or press Ctrl+Alt+R anytime!",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _toggle_circle(self):
        if self.circle_widget.isVisible():
            self.circle_widget.hide()
        else:
            self.circle_widget.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_circle()

    def _on_settings_updated(self):
        visible = settings.get("circle_visible", True)
        if visible:
            self.circle_widget.show()
        else:
            self.circle_widget.hide()
        if hasattr(self, "auto_read_action"):
            self.auto_read_action.setChecked(settings.get("auto_read_clipboard", False))
        # Restart hotkeys in case bindings changed
        hotkey_manager.start()

    def _exit_app(self):
        self.selection_popover.stop()
        tts_engine.stop()
        hotkey_manager.stop()
        self.tray.hide()
        self.qapp.quit()



def main():
    # 1. Single Instance Check
    mutex = acquire_single_instance_mutex()
    if not mutex:
        print("[Main] ReadAloud AI is already running.")
        sys.exit(0)

    # 2. Qt Application Setup
    # Enable DPI awareness on Windows 11
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ReadAloud Desktop AI")
    app.setApplicationDisplayName("ReadAloud Desktop AI")
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    # Initialize Controller
    read_aloud_app = ReadAloudApp(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
