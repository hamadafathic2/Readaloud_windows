# ReadAloud Desktop AI 🔊

A modern Windows 11 desktop application to read any English text anywhere on your screen using **100% local, natural neural AI sound**. Features a floating circular controller, fullscreen snipping OCR, and a standard Windows installer.

---

## 📥 Direct Download & Installation (Windows 10 / 11)

No coding or Python installation needed! Anyone can install and run **ReadAloud Desktop AI** in seconds:

[![Download Windows Installer](https://img.shields.io/badge/Download-Windows_Installer_(v1.0.0)-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/hamadafathic2/Readaloud_windows/releases/download/v1.0.0/ReadAloud-Setup-v1.0.exe)

| Package | Download Link | Description | Size |
| :--- | :--- | :--- | :--- |
| **Windows Setup Wizard** *(Recommended)* | [**`ReadAloud-Setup-v1.0.exe`**](https://github.com/hamadafathic2/Readaloud_windows/releases/download/v1.0.0/ReadAloud-Setup-v1.0.exe) | Official Windows 11 setup wizard with Start Menu & Desktop shortcuts | ~135 MB |
| **All Releases & Updates** | [**GitHub Releases**](https://github.com/hamadafathic2/Readaloud_windows/releases) | Changelog, checksums, and version history | — |

### How to Install:
1. Download [**`ReadAloud-Setup-v1.0.exe`**](https://github.com/hamadafathic2/Readaloud_windows/releases/download/v1.0.0/ReadAloud-Setup-v1.0.exe).
2. Double-click the installer and follow the standard Windows Setup wizard.
3. Launch **ReadAloud Desktop AI** from your Start Menu or Desktop!
4. Select any text on your screen and press `Ctrl + Alt + R` or click the floating circle to read it aloud.

## ✨ Features

- **🗣 100% Local Neural AI Sound**:
  - Powered by **Kokoro-ONNX**, an 82M open-source neural acoustic model.
  - Sounds like a human narrator — expressive, rhythmic, and natural.
  - Runs completely offline on CPU with zero internet or cloud fees.
  - Multiple curated voices: **Heart** (US Female, Recommended), **Bella**, **Adam** (US Male), **Michael**, **Emma** (UK Female), **George** (UK Male), etc.
- **📄 Read Any Text Anywhere**:
  - **Highlight & Read**: Select any words in any app (Chrome, Word, PDFs, Discord, code editor, etc.) and press `Ctrl + Alt + R` or click the circle.
  - **Snip & Read Screen (OCR)**: Drag a box around text in images, games, or locked documents to extract and read it aloud instantly with local **RapidOCR**.
- **🔵 Floating Cosmic Black Hole Controller**:
  - Frameless, translucent Windows 11 Fluent widget that stays on top.
  - Smoothly draggable anywhere; snaps to screen edges; remembers its position.
  - Dynamic live visualizer: static central Black Hole event horizon with surrounding voice-reactive stardust accretion disk and lensing rings.
  - Radial flyout controls: **Close App (✕)**, **Play/Pause (⏯)**, **Stop (⏹)**, **Snip (✂)**, **Speed** (0.8x - 2.0x), **Voice Switcher (🗣)**, and **Settings (⚙)**.
- **💻 Standard Windows 11 Installer**:
  - Compiles into a standard `.exe` setup wizard (`ReadAloud-Setup-v1.0.exe`).
  - Installs to Program Files, creates Start Menu and Desktop shortcuts, and registers in Windows Settings for easy uninstallation.

---

## ⌨️ Shortcuts & Controls

| Action | Shortcut / Trigger |
| :--- | :--- |
| **Read Selected Text** | `Ctrl + Alt + R` or **Click Floating Circle** |
| **Snip & Read Screen (OCR)** | `Ctrl + Alt + S` or **Click ✂ Satellite Button** |
| **Play / Pause** | **Click Circle** (while speaking) or **Click ⏯ Satellite Button** |
| **Close App** | **Click ✕ Satellite Button** (next to Play/Pause) |
| **Stop** | **Click ⏹ Satellite Button** |
| **Cycle Speech Speed** | **Click ⚡ Satellite Button** (0.8x → 1.0x → 1.25x → 1.5x → 2.0x) |
| **Switch AI Voice** | **Click 🗣 Satellite Button** |
| **Open Settings** | **Click ⚙ Satellite Button** or Right-click Circle |
| **Cancel Snipping** | `ESC` or **Right-Click** |

---

## 🚀 Quick Start (Development)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the application**:
   - Double-click `run.bat` or run:
     ```bash
     python src/main.py
     ```
   - On first launch, the app will automatically download the Kokoro neural voice weights (~320 MB) into `%APPDATA%\ReadAloudAI\models\`. Once finished, the app works 100% offline.

---

## 📦 Building the Windows 11 Installer

To package the application into a standalone Windows installer wizard:

1. Double click `build_installer.bat`
2. PyInstaller will compile the app and its dependencies into `dist/ReadAloudAI/`.
3. Inno Setup will compile the installer into `output/ReadAloud-Setup-v1.0.exe`.
4. Run `ReadAloud-Setup-v1.0.exe` on any Windows 10/11 PC to install it normally!

---

## 📁 Project Architecture

```
├── assets/
│   ├── icon.ico                 # Multi-res application icon
│   └── icon.png                 # Branded app logo
├── src/
│   ├── main.py                  # Single-instance mutex, tray icon, app coordinator
│   ├── config/
│   │   └── settings.py          # Persistent configuration in %APPDATA%
│   ├── audio/
│   │   ├── voice_manager.py     # Kokoro neural model manager & voice registry
│   │   ├── player.py            # Low-latency audio streamer with amplitude analyzer
│   │   └── tts_engine.py        # Sentence streaming pipeline & SAPI fallback
│   ├── capture/
│   │   ├── text_grabber.py      # Active window text selection grabber
│   │   ├── ocr_engine.py        # RapidOCR local screen recognition
│   │   └── hotkeys.py           # Global background keyboard listener
│   └── ui/
│       ├── floating_circle.py   # Draggable circular controller with audio pulse
│       ├── snip_overlay.py      # Semi-transparent screen snipping tool
│       ├── settings_dialog.py   # Windows 11 Fluent settings window
│       ├── download_dialog.py   # First-launch model download progress
│       └── styles.py            # Fluent dark theme and SVG icons
├── installer/
│   ├── ReadAloud.spec           # PyInstaller build specification
│   └── setup.iss                # Inno Setup installation wizard script
├── requirements.txt
├── run.bat
└── build_installer.bat
```
