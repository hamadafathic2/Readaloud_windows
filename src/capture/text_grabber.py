import time
import ctypes
from ctypes import wintypes
from typing import Optional
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Virtual Key Codes
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_C = 0x43
VK_A = 0x41
VK_R = 0x52
VK_S = 0x53
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001


class WindowTracker:
    """Tracks the last active external (non-ReadAloud) application window.

    Ensures that when clicking the floating circle or triggering hotkeys,
    the synthetic Ctrl+C is sent to the application the user was actually reading.
    """

    def __init__(self):
        self.last_external_hwnd: Optional[int] = None
        self._own_pids = {kernel32.GetCurrentProcessId()}

    def register_own_pid(self, pid: int):
        self._own_pids.add(pid)

    def record_foreground(self):
        """Record current foreground window if it is not a ReadAloud window."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value and pid.value not in self._own_pids:
            self.last_external_hwnd = hwnd

    def ensure_target_focus(self):
        """Restore focus to the target window if ReadAloud currently holds focus."""
        curr_hwnd = user32.GetForegroundWindow()
        if not curr_hwnd:
            if self.last_external_hwnd:
                user32.SetForegroundWindow(self.last_external_hwnd)
                time.sleep(0.04)
            return

        curr_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(curr_hwnd, ctypes.byref(curr_pid))
        if curr_pid.value in self._own_pids and self.last_external_hwnd:
            try:
                cur_thread = kernel32.GetCurrentThreadId()
                target_thread = user32.GetWindowThreadProcessId(self.last_external_hwnd, None)
                user32.AttachThreadInput(cur_thread, target_thread, True)
                user32.SetForegroundWindow(self.last_external_hwnd)
                user32.AttachThreadInput(cur_thread, target_thread, False)
                time.sleep(0.04)
            except Exception as e:
                print(f"[WindowTracker] Error refocusing target window: {e}")


window_tracker = WindowTracker()


def release_modifier_keys():
    """Ensure Alt, Ctrl, Shift, and Win keys are released in the OS input state.

    When global hotkeys like Ctrl+Alt+R trigger, the user's fingers are still physically
    pressing Alt and Ctrl down. If Alt remains down, simulating Ctrl+C sends Ctrl+Alt+C
    to the active window, which fails to copy. This function releases all modifiers.
    """
    keys_to_release = [
        VK_MENU, VK_LMENU, VK_RMENU,
        VK_CONTROL, VK_LCONTROL, VK_RCONTROL,
        VK_SHIFT, VK_LWIN, VK_RWIN,
        VK_R, VK_S,
    ]
    for vk in keys_to_release:
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)


def send_ctrl_c():
    """Simulate a pure Ctrl+C keystroke using Win32 keybd_event with pynput fallback."""
    try:
        scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        scan_c = user32.MapVirtualKeyW(VK_C, 0)

        # Press Ctrl
        user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
        time.sleep(0.02)
        # Press C
        user32.keybd_event(VK_C, scan_c, 0, 0)
        time.sleep(0.03)
        # Release C
        user32.keybd_event(VK_C, scan_c, KEYEVENTF_KEYUP, 0)
        time.sleep(0.015)
        # Release Ctrl
        user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[TextGrabber] keybd_event error: {e}, attempting pynput fallback...")
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            kb.release(Key.alt)
            kb.release(Key.ctrl)
            with kb.pressed(Key.ctrl):
                kb.press('c')
                time.sleep(0.02)
                kb.release('c')
        except Exception as pe:
            print(f"[TextGrabber] pynput fallback failed: {pe}")


def get_uia_selected_text() -> str:
    """Attempt to get selected text via Windows UI Automation directly from the focused element.

    Works with zero clipboard disruption in Chromium, Word, Edge, Notepad, and UIA-aware controls.
    """
    try:
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        try:
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=mod.IUIAutomation)
            elem = uia.GetFocusedElement()
            if not elem:
                return ""

            # 10014 = UIA_TextPatternId, 10024 = UIA_TextPattern2Id
            for pat_id in (10014, 10024):
                try:
                    pat = elem.GetCurrentPattern(pat_id)
                    if pat:
                        tp = pat.QueryInterface(mod.IUIAutomationTextPattern)
                        selection = tp.GetSelection()
                        if selection and selection.Length > 0:
                            txt_range = selection.GetElement(0)
                            txt = txt_range.GetText(-1)
                            if txt and txt.strip():
                                return txt.strip()
                except Exception:
                    continue
        finally:
            comtypes.CoUninitialize()
    except Exception:
        pass
    return ""


class TextGrabber:
    """Grabs selected text from any active application window on Windows 11."""

    @staticmethod
    def get_selected_text(timeout: float = 0.40, restore_clipboard: bool = False) -> str:
        """Grabs the currently selected/highlighted text across any Windows app.

        Pipeline:
        1. Record/ensure active target application has focus.
        2. Attempt Windows UI Automation (silent, instant, no clipboard change).
        3. Release Alt/Ctrl modifier keys so hotkeys do not interfere with Ctrl+C.
        4. Record current clipboard sequence number and content.
        5. Send synthetic Ctrl+C via Win32 keybd_event.
        6. Poll for clipboard sequence number increment or content update.
        7. Optionally restore previous clipboard content if desired.
        8. Return newly selected text.
        """
        # Step 1: Ensure target window is focused
        window_tracker.ensure_target_focus()

        # Step 2: Check Windows UI Automation
        uia_text = get_uia_selected_text()
        if uia_text:
            return uia_text

        # Step 3: Release modifiers before sending Ctrl+C
        release_modifier_keys()
        time.sleep(0.04)

        # Step 4: Record current clipboard state
        seq_before = user32.GetClipboardSequenceNumber()
        prev_clipboard = ""
        try:
            prev_clipboard = pyperclip.paste()
        except Exception:
            pass

        # Step 5: Send synthetic Ctrl+C to active foreground window
        send_ctrl_c()

        # Step 6: Wait for clipboard sequence to increment (indicates new copy)
        start = time.time()
        new_text = ""
        while time.time() - start < timeout:
            time.sleep(0.02)
            try:
                curr_seq = user32.GetClipboardSequenceNumber()
                if curr_seq != seq_before:
                    content = pyperclip.paste()
                    if content and content.strip():
                        new_text = content.strip()
                        break
            except Exception:
                pass

        if not new_text:
            # Direct paste check (for apps that update content without sequence bump)
            try:
                latest = pyperclip.paste()
                if latest and latest.strip() and latest.strip() != prev_clipboard.strip():
                    new_text = latest.strip()
            except Exception:
                pass

        # Step 7: Optionally restore previous clipboard if requested
        if new_text and restore_clipboard and prev_clipboard:
            try:
                def _restore():
                    time.sleep(0.2)
                    try:
                        pyperclip.copy(prev_clipboard)
                    except Exception:
                        pass
                import threading
                threading.Thread(target=_restore, daemon=True).start()
            except Exception:
                pass

        return new_text


text_grabber = TextGrabber()

