import json
import os
import sys
import winreg
from pathlib import Path
from typing import Any, Dict


class AppSettings:
    """Manages application configuration, user preferences, and Windows autostart."""

    APP_NAME = "ReadAloudAI"
    DEFAULT_SETTINGS: Dict[str, Any] = {
        "voice": "af_heart",
        "speed": 1.0,
        "volume": 1.0,
        "circle_pos_x": -1,
        "circle_pos_y": -1,
        "circle_visible": True,
        "circle_size": 64,
        "hotkey_read_selection": "<ctrl>+<alt>+r",
        "hotkey_snip_read": "<ctrl>+<alt>+s",
        "auto_read_clipboard": False,
        "show_selection_popover": True,
        "restore_clipboard_after_read": True,
        "start_with_windows": False,
        "theme": "dark",
        "show_subtitles": True,
    }

    def __init__(self):
        self.app_dir = Path(os.environ.get("APPDATA", Path.home())) / self.APP_NAME
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir = self.app_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.app_dir / "config.json"
        self.data: Dict[str, Any] = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        """Load settings from JSON file with fallback to defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Settings] Error loading config: {e}. Using defaults.")
        self.save()

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Settings] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    @property
    def voice(self) -> str:
        return self.get("voice", "af_heart")

    @voice.setter
    def voice(self, val: str):
        self.set("voice", val)

    @property
    def speed(self) -> float:
        return float(self.get("speed", 1.0))

    @speed.setter
    def speed(self, val: float):
        self.set("speed", max(0.5, min(2.5, float(val))))

    @property
    def volume(self) -> float:
        return float(self.get("volume", 1.0))

    @volume.setter
    def volume(self, val: float):
        self.set("volume", max(0.0, min(1.0, float(val))))

    @property
    def circle_pos(self) -> tuple[int, int]:
        return int(self.get("circle_pos_x", -1)), int(self.get("circle_pos_y", -1))

    def set_circle_pos(self, x: int, y: int):
        self.data["circle_pos_x"] = int(x)
        self.data["circle_pos_y"] = int(y)
        self.save()

    @property
    def start_with_windows(self) -> bool:
        return bool(self.get("start_with_windows", False))

    @start_with_windows.setter
    def start_with_windows(self, enable: bool):
        self.set("start_with_windows", enable)
        self.configure_windows_startup(enable)

    def configure_windows_startup(self, enable: bool) -> bool:
        """Add or remove application from Windows Run registry key."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "ReadAloudAI"

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS
            ) as key:
                if enable:
                    if getattr(sys, "frozen", False):
                        exe_path = f'"{sys.executable}"'
                    else:
                        exe_path = f'"{sys.executable}" "{Path(__file__).parent.parent / "main.py"}"'
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            print(f"[Settings] Error configuring startup: {e}")
            return False


# Global singleton instance
settings = AppSettings()
