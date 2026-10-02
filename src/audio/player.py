import threading
import time
import queue
from typing import Callable, Optional
import numpy as np
import sounddevice as sd
from ..config.settings import settings


class AudioItem:
    def __init__(self, samples: np.ndarray, sample_rate: int, text: str = ""):
        self.samples = samples
        self.sample_rate = sample_rate
        self.text = text


class AudioPlayer:
    """Thread-safe low-latency audio player with pause/resume, stop, volume,

    and real-time amplitude callbacks for UI wave visualization.
    """

    STATE_IDLE = "idle"
    STATE_PLAYING = "playing"
    STATE_PAUSED = "paused"

    def __init__(self):
        self._queue: queue.Queue[Optional[AudioItem]] = queue.Queue()
        self._state = self.STATE_IDLE
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.on_amplitude: Optional[Callable[[float], None]] = None
        self.on_sentence: Optional[Callable[[str], None]] = None

        self._start_worker()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def _set_state(self, new_state: str):
        with self._lock:
            if self._state == new_state:
                return
            self._state = new_state
        if self.on_state_changed:
            try:
                self.on_state_changed(new_state)
            except Exception as e:
                print(f"[AudioPlayer] on_state_changed error: {e}")

    def _start_worker(self):
        self._worker_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._worker_thread.start()

    def enqueue(self, item: AudioItem):
        """Queue a sentence/chunk for playback."""
        self._queue.put(item)

    def pause(self):
        if self.state == self.STATE_PLAYING:
            self._pause_event.clear()
            self._set_state(self.STATE_PAUSED)

    def resume(self):
        if self.state == self.STATE_PAUSED:
            self._pause_event.set()
            self._set_state(self.STATE_PLAYING)

    def toggle_play_pause(self):
        if self.state == self.STATE_PLAYING:
            self.pause()
        elif self.state == self.STATE_PAUSED:
            self.resume()

    def stop(self):
        """Immediately stop playback and discard pending audio queue."""
        self._stop_event.set()
        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._pause_event.set()  # Unblock in case paused
        self._set_state(self.STATE_IDLE)
        if self.on_amplitude:
            self.on_amplitude(0.0)

    def _playback_loop(self):
        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                if self.state != self.STATE_PAUSED and self.state != self.STATE_IDLE:
                    self._set_state(self.STATE_IDLE)
                    if self.on_amplitude:
                        self.on_amplitude(0.0)
                continue

            if item is None:
                continue

            self._stop_event.clear()
            self._set_state(self.STATE_PLAYING)

            if item.text and self.on_sentence:
                try:
                    self.on_sentence(item.text)
                except Exception:
                    pass

            samples = item.samples
            sample_rate = item.sample_rate

            # Ensure 1D float32
            if samples.dtype != np.float32:
                samples = samples.astype(np.float32)

            volume = settings.volume
            if volume < 0.99:
                samples = samples * volume

            chunk_size = 1024
            total_samples = len(samples)
            idx = 0

            try:
                with sd.OutputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size,
                ) as stream:
                    while idx < total_samples:
                        if self._stop_event.is_set():
                            break

                        # Wait if paused
                        self._pause_event.wait()
                        if self._stop_event.is_set():
                            break

                        end_idx = min(idx + chunk_size, total_samples)
                        chunk = samples[idx:end_idx]

                        # Apply current volume setting dynamically
                        curr_vol = settings.volume
                        if curr_vol < 0.99:
                            chunk = chunk * curr_vol

                        # Pad if needed
                        if len(chunk) < chunk_size:
                            chunk_padded = np.zeros(chunk_size, dtype=np.float32)
                            chunk_padded[: len(chunk)] = chunk
                            stream.write(chunk_padded)
                        else:
                            stream.write(chunk)

                        # Calculate RMS amplitude for real-time visualization
                        rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                        amp = min(1.0, rms * 4.0)  # scale for UI visibility
                        if self.on_amplitude:
                            self.on_amplitude(amp)

                        idx = end_idx

            except Exception as e:
                print(f"[AudioPlayer] Playback error: {e}")

            if self.on_amplitude:
                self.on_amplitude(0.0)

            self._queue.task_done()


player = AudioPlayer()
