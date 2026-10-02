import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable, Dict, List, Optional
from ..config.settings import settings


class VoiceInfo:
    def __init__(self, id: str, name: str, gender: str, accent: str, description: str):
        self.id = id
        self.name = name
        self.gender = gender
        self.accent = accent
        self.description = description

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.accent} {self.gender}) - {self.description}"


class VoiceManager:
    """Manages neural AI voice models, downloads, and voice metadata."""

    MODEL_FILENAME = "kokoro-v1.0.onnx"
    VOICES_FILENAME = "voices-v1.0.bin"

    MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
    VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

    # Curated high quality English neural voices
    AVAILABLE_VOICES: List[VoiceInfo] = [
        VoiceInfo("af_heart", "Heart", "Female", "US", "Warm, natural & expressive (Recommended)"),
        VoiceInfo("af_bella", "Bella", "Female", "US", "Melodic, lively & articulate"),
        VoiceInfo("af_sarah", "Sarah", "Female", "US", "Soft, professional & calm"),
        VoiceInfo("af_sky", "Sky", "Female", "US", "Bright, friendly & casual"),
        VoiceInfo("af_nicole", "Nicole", "Female", "US", "Crisp & clear conversational"),
        VoiceInfo("am_adam", "Adam", "Male", "US", "Deep, confident & engaging"),
        VoiceInfo("am_michael", "Michael", "Male", "US", "Natural, friendly & smooth"),
        VoiceInfo("am_echo", "Echo", "Male", "US", "Dynamic & punchy narrator"),
        VoiceInfo("bf_emma", "Emma", "Female", "UK", "British refined, gentle & clear"),
        VoiceInfo("bf_isabella", "Isabella", "Female", "UK", "British calm & articulate"),
        VoiceInfo("bm_george", "George", "Male", "UK", "British warm, classic & authoritative"),
        VoiceInfo("bm_lewis", "Lewis", "Male", "UK", "British engaging & modern"),
    ]

    def __init__(self):
        self.models_dir = settings.models_dir
        self.model_path = self.models_dir / self.MODEL_FILENAME
        self.voices_path = self.models_dir / self.VOICES_FILENAME

    def is_ready(self) -> bool:
        """Check if local AI neural model and voice files exist and are valid."""
        return (
            self.model_path.exists()
            and self.model_path.stat().st_size > 10_000_000
            and self.voices_path.exists()
            and self.voices_path.stat().st_size > 1_000_000
        )

    def get_voices(self) -> List[VoiceInfo]:
        return self.AVAILABLE_VOICES

    def get_voice_by_id(self, voice_id: str) -> Optional[VoiceInfo]:
        for v in self.AVAILABLE_VOICES:
            if v.id == voice_id:
                return v
        return self.AVAILABLE_VOICES[0] if self.AVAILABLE_VOICES else None

    def download_file(
        self,
        url: str,
        target_path: Path,
        label: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> bool:
        """Download file with chunked streaming and percentage updates."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ReadAloudDesktopAI/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 256  # 256 KB

                with open(temp_path, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(label, downloaded, total_size)

            if temp_path.exists():
                if target_path.exists():
                    target_path.unlink()
                temp_path.rename(target_path)
            return True
        except Exception as e:
            print(f"[VoiceManager] Download failed for {label}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False

    def ensure_models(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> bool:
        """Ensure model and voice files exist, downloading them if missing."""
        if not self.model_path.exists() or self.model_path.stat().st_size < 10_000_000:
            ok = self.download_file(
                self.MODEL_URL,
                self.model_path,
                "Downloading Neural Voice Engine (320 MB)...",
                progress_callback,
            )
            if not ok:
                return False

        if not self.voices_path.exists() or self.voices_path.stat().st_size < 1_000_000:
            ok = self.download_file(
                self.VOICES_URL,
                self.voices_path,
                "Downloading Voice Library (28 MB)...",
                progress_callback,
            )
            if not ok:
                return False

        return True


voice_manager = VoiceManager()
