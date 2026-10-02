import re
import threading
import time
from typing import Callable, List, Optional
import numpy as np
from ..config.settings import settings
from .voice_manager import voice_manager
from .player import AudioItem, player

try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class TTSEngine:
    """High-performance text-to-speech engine supporting Kokoro neural ONNX

    with streaming sentence pipelining and Windows SAPI fallback.
    """

    def __init__(self):
        self._kokoro_instance = None
        self._kokoro_lock = threading.Lock()
        self._synthesis_lock = threading.Lock()
        self._current_thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self.is_synthesizing = False

        # Callbacks
        self.on_start: Optional[Callable[[], None]] = None
        self.on_sentence: Optional[Callable[[str], None]] = None
        self.on_finish: Optional[Callable[[], None]] = None
        self.on_prepare_progress: Optional[Callable[[Optional[float]], None]] = None

    def _emit_progress(self, progress: Optional[float]):
        if self.on_prepare_progress:
            try:
                self.on_prepare_progress(progress)
            except Exception as e:
                print(f"[TTSEngine] on_prepare_progress error: {e}")

    def _get_kokoro(self):
        if self._kokoro_instance is not None:
            return self._kokoro_instance

        if not voice_manager.is_ready():
            return None

        with self._kokoro_lock:
            if self._kokoro_instance is None and Kokoro is not None:
                try:
                    print("[TTSEngine] Initializing Kokoro Neural AI Model...")
                    self._kokoro_instance = Kokoro(
                        model_path=str(voice_manager.model_path),
                        voices_path=str(voice_manager.voices_path),
                    )
                    print("[TTSEngine] Kokoro Neural AI Model initialized successfully!")
                except Exception as e:
                    print(f"[TTSEngine] Error initializing Kokoro: {e}")
                    self._kokoro_instance = None
        return self._kokoro_instance

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text into natural speaking sentences while respecting abbreviations."""
        text = re.sub(r"\r\n|\r|\n", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        # Temporarily protect common abbreviations
        abbrevs = ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "vs.", "etc.", "i.e.", "e.g."]
        for i, abbr in enumerate(abbrevs):
            text = text.replace(abbr, f"__ABBR_{i}__")

        # Split on sentence terminals (.?!;:) followed by whitespace
        parts = re.split(r"(?<=[.?!;:])\s+", text)
        sentences = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Restore abbreviations
            for i, abbr in enumerate(abbrevs):
                p = p.replace(f"__ABBR_{i}__", abbr)

            # If sentence is extremely long (>250 chars) without punctuation, split by commas
            if len(p) > 250:
                sub_parts = re.split(r"(?<=,)\s+", p)
                for sp in sub_parts:
                    if sp.strip():
                        sentences.append(sp.strip())
            else:
                sentences.append(p)
        return sentences

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ):
        """Cancel any existing speech and start synthesizing new text."""
        self.stop()
        if self._current_thread and self._current_thread.is_alive():
            self._current_thread.join(timeout=0.15)

        clean_text = text.strip()
        if not clean_text:
            return

        self._cancel_event.clear()
        self._emit_progress(0.06)
        voice_id = voice or settings.voice
        curr_speed = speed if speed is not None else settings.speed

        self._current_thread = threading.Thread(
            target=self._synthesize_and_stream,
            args=(clean_text, voice_id, curr_speed),
            daemon=True,
        )
        self._current_thread.start()

    def stop(self):
        """Immediately stop synthesis and audio playback."""
        self._cancel_event.set()
        player.stop()
        self.is_synthesizing = False
        self._emit_progress(None)
        if self.on_finish:
            try:
                self.on_finish()
            except Exception:
                pass

    def _synthesize_and_stream(self, text: str, voice_id: str, speed: float):
        self.is_synthesizing = True
        self._emit_progress(0.15)
        if self.on_start:
            try:
                self.on_start()
            except Exception:
                pass

        kokoro = self._get_kokoro()
        self._emit_progress(0.32)
        sentences = self.split_sentences(text)

        if not sentences:
            self.is_synthesizing = False
            self._emit_progress(None)
            return

        self._emit_progress(0.45)

        # Check if Kokoro is available
        if kokoro is not None:
            # Neural Kokoro AI synthesis
            lang = "en-gb" if voice_id.startswith("b") else "en-us"
            first_chunk_done = False

            for sentence in sentences:
                if self._cancel_event.is_set():
                    break

                # Skip sentences without any pronounceable alphanumeric characters
                if not any(c.isalnum() for c in sentence):
                    continue

                if self.on_sentence:
                    try:
                        self.on_sentence(sentence)
                    except Exception:
                        pass

                try:
                    if not first_chunk_done:
                        self._emit_progress(0.60)

                    with self._synthesis_lock:
                        if self._cancel_event.is_set():
                            break
                        samples, sample_rate = kokoro.create(
                            text=sentence,
                            voice=voice_id,
                            speed=speed,
                            lang=lang,
                        )

                    if self._cancel_event.is_set():
                        break

                    player.enqueue(AudioItem(samples, sample_rate, text=sentence))

                    if not first_chunk_done:
                        first_chunk_done = True
                        self._emit_progress(1.0)
                except Exception as e:
                    print(f"[TTSEngine] Kokoro error on '{sentence[:30]}...': {e}. Falling back to SAPI...")
                    try:
                        self._fallback_sapi_speak([sentence], speed)
                    except Exception as sapi_err:
                        print(f"[TTSEngine] SAPI fallback error: {sapi_err}")
        else:
            # Fallback to SAPI5 if Kokoro is still downloading or unready
            print("[TTSEngine] Using Windows SAPI fallback...")
            self._emit_progress(0.70)
            self._fallback_sapi_speak(sentences, speed)

        self.is_synthesizing = False

    def _fallback_sapi_speak(self, sentences: List[str], speed: float):
        if pyttsx3 is None:
            print("[TTSEngine] pyttsx3 not available.")
            return

        try:
            engine = pyttsx3.init()
            # Set rate: normal is around 200 wpm
            base_rate = 190
            engine.setProperty("rate", int(base_rate * speed))
            engine.setProperty("volume", settings.volume)

            for sentence in sentences:
                if self._cancel_event.is_set():
                    break
                if self.on_sentence:
                    self.on_sentence(sentence)
                engine.say(sentence)
                engine.runAndWait()
        except Exception as e:
            print(f"[TTSEngine] SAPI error: {e}")


tts_engine = TTSEngine()
