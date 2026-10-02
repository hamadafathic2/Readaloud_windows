import threading
import time
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
from pynput import keyboard
from ..config.settings import settings

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_R = 0x52
VK_S = 0x53

HOTKEY_ID_READ = 1
HOTKEY_ID_SNIP = 2


class Win32HotkeyThread(threading.Thread):
    """Native Windows message-loop thread listening for WM_HOTKEY events.
    
    Zero-hook overhead, immune to low-level hook timeouts, and 100% reliable.
    """

    def __init__(self, on_read: Optional[Callable[[], None]], on_snip: Optional[Callable[[], None]]):
        super().__init__(daemon=True)
        self.on_read = on_read
        self.on_snip = on_snip
        self.thread_id: Optional[int] = None
        self.ready_event = threading.Event()
        self.running = False
        self.success = False

    def run(self):
        self.thread_id = kernel32.GetCurrentThreadId()

        # Register Ctrl+Alt+R and Ctrl+Alt+S with MOD_NOREPEAT
        res_read = user32.RegisterHotKey(
            None, HOTKEY_ID_READ, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_R
        )
        res_snip = user32.RegisterHotKey(
            None, HOTKEY_ID_SNIP, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_S
        )

        if res_read or res_snip:
            self.success = True
            print(f"[Win32Hotkey] Native Windows hotkeys registered (Read: {bool(res_read)}, Snip: {bool(res_snip)})")
        else:
            self.success = False
            print(f"[Win32Hotkey] Could not register native hotkeys. Error: {kernel32.GetLastError()}")

        self.ready_event.set()
        if not self.success:
            return

        self.running = True
        msg = wintypes.MSG()
        while self.running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_READ and self.on_read:
                    threading.Thread(target=self._safe_call, args=(self.on_read,), daemon=True).start()
                elif msg.wParam == HOTKEY_ID_SNIP and self.on_snip:
                    threading.Thread(target=self._safe_call, args=(self.on_snip,), daemon=True).start()

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnregisterHotKey(None, HOTKEY_ID_READ)
        user32.UnregisterHotKey(None, HOTKEY_ID_SNIP)

    def _safe_call(self, func: Callable[[], None]):
        try:
            func()
        except Exception as e:
            print(f"[Win32Hotkey] Callback error: {e}")

    def stop(self):
        self.running = False
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


class HotkeyManager:
    """Manages global system-wide hotkeys for reading selection and screen snipping."""

    def __init__(self):
        self._win32_thread: Optional[Win32HotkeyThread] = None
        self._pynput_listener: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()
        self.on_read_selection: Optional[Callable[[], None]] = None
        self.on_snip_read: Optional[Callable[[], None]] = None

    def start(self):
        self.stop()

        hotkey_read = settings.get("hotkey_read_selection", "<ctrl>+<alt>+r").lower()
        hotkey_snip = settings.get("hotkey_snip_read", "<ctrl>+<alt>+s").lower()

        # If using standard shortcuts on Windows, prefer native RegisterHotKey
        if hotkey_read == "<ctrl>+<alt>+r" and hotkey_snip == "<ctrl>+<alt>+s":
            self._win32_thread = Win32HotkeyThread(
                on_read=self._handle_read_selection,
                on_snip=self._handle_snip_read,
            )
            self._win32_thread.start()
            self._win32_thread.ready_event.wait(timeout=1.0)
            if self._win32_thread.success:
                return

        # Fallback to pynput if custom hotkeys or if RegisterHotKey was taken
        bindings = {}
        if hotkey_read and self.on_read_selection:
            bindings[hotkey_read] = self._handle_read_selection
        if hotkey_snip and self.on_snip_read:
            bindings[hotkey_snip] = self._handle_snip_read

        if bindings:
            try:
                self._pynput_listener = keyboard.GlobalHotKeys(bindings)
                self._pynput_listener.daemon = True
                self._pynput_listener.start()
                print(f"[HotkeyManager] Registered pynput global hotkeys: {list(bindings.keys())}")
            except Exception as e:
                print(f"[HotkeyManager] Error registering pynput hotkeys: {e}")

    def stop(self):
        if self._win32_thread is not None:
            self._win32_thread.stop()
            self._win32_thread = None

        if self._pynput_listener is not None:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass
            self._pynput_listener = None

    def _handle_read_selection(self):
        if self.on_read_selection:
            threading.Thread(target=self._run_safe, args=(self.on_read_selection,), daemon=True).start()

    def _handle_snip_read(self):
        if self.on_snip_read:
            threading.Thread(target=self._run_safe, args=(self.on_snip_read,), daemon=True).start()

    def _run_safe(self, callback):
        try:
            callback()
        except Exception as e:
            print(f"[HotkeyManager] Callback error: {e}")


hotkey_manager = HotkeyManager()
