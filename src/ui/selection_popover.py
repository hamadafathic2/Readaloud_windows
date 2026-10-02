import time
import math
import ctypes
from ctypes import wintypes
from typing import Optional

from PyQt6.QtCore import (
    Qt,
    QPoint,
    QRectF,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QFont,
    QCursor,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
)

from ..config.settings import settings
from ..capture.text_grabber import text_grabber, window_tracker
from .styles import COLORS

try:
    from pynput import mouse
except ImportError:
    mouse = None


class SelectionPopover(QWidget):
    """A sleek floating mini pill [🔊 Read] appearing near the mouse cursor

    when the user finishes highlighting text in any Windows application.
    Non-activating: clicking it never steals focus from the target document.
    """

    request_read = pyqtSignal(str)
    _sig_drag_detected = pyqtSignal()
    _sig_click_elsewhere = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()

        # Register with window tracker
        window_tracker.register_own_pid(ctypes.windll.kernel32.GetCurrentProcessId())

        # Non-activating, frameless, always-on-top tooltip style
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.setFixedSize(92, 34)
        self.is_hovered = False

        # Connect thread-safe internal signals
        self._sig_drag_detected.connect(self._on_drag_detected)
        self._sig_click_elsewhere.connect(self._on_click_elsewhere)

        # Auto-hide timer (disappears after 2.8 seconds)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(2800)
        self.hide_timer.timeout.connect(self.hide_popover)

        # Mouse selection monitor
        self._mouse_listener: Optional[mouse.Listener] = None
        self._drag_start_pos = (0, 0)
        self._is_left_down = False
        self._drag_threshold = 28  # Pixels of drag distance to consider a selection

        self._start_mouse_monitor()



    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            WM_MOUSEACTIVATE = 0x0021
            MA_NOACTIVATE = 3
            if msg.message == WM_MOUSEACTIVATE:
                return True, MA_NOACTIVATE
        return False, 0


    def _start_mouse_monitor(self):
        if mouse is None:
            return

        def on_click(x, y, button, pressed):
            if not settings.get("show_selection_popover", True):
                return

            if button == mouse.Button.left:
                if pressed:
                    self._is_left_down = True
                    self._drag_start_pos = (x, y)
                    self._sig_click_elsewhere.emit(int(x), int(y))
                else:
                    if self._is_left_down:
                        self._is_left_down = False
                        dx = x - self._drag_start_pos[0]
                        dy = y - self._drag_start_pos[1]
                        dist = math.hypot(dx, dy)
                        if dist >= self._drag_threshold:
                            # User dragged mouse across screen: likely selected text!
                            window_tracker.record_foreground()
                            self._sig_drag_detected.emit()

        try:
            self._mouse_listener = mouse.Listener(on_click=on_click)
            self._mouse_listener.daemon = True
            self._mouse_listener.start()
        except Exception as e:
            print(f"[SelectionPopover] Mouse monitor error: {e}")

    def _on_drag_detected(self):
        if not settings.get("show_selection_popover", True):
            return
        QTimer.singleShot(60, self._do_show_near_cursor)

    def _on_click_elsewhere(self, x: int, y: int):
        if self.isVisible() and not self.geometry().contains(x, y):
            self.hide_popover()

    def _do_show_near_cursor(self):
        if not settings.get("show_selection_popover", True):
            return

        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else self.geometry()

        # Position slightly above and to the right of cursor
        target_x = cursor_pos.x() + 12
        target_y = cursor_pos.y() - 40

        # Boundary checks
        if target_x + self.width() > screen_geo.right() - 10:
            target_x = cursor_pos.x() - self.width() - 12
        if target_y < screen_geo.top() + 10:
            target_y = cursor_pos.y() + 24

        self.move(int(target_x), int(target_y))
        self.show()
        self.hide_timer.start()

    def hide_popover(self):
        self.hide_timer.stop()
        self.hide()

    def enterEvent(self, event):
        self.is_hovered = True
        self.hide_timer.stop()  # Don't auto-hide while hovering over button
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.hide_timer.start()  # Resume auto-hide countdown
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_popover()
            # Grab selected text from the target window
            text = text_grabber.get_selected_text(
                restore_clipboard=settings.get("restore_clipboard_after_read", True)
            )
            if text and text.strip():
                self.request_read.emit(text.strip())
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        # Background fill
        if self.is_hovered:
            bg_color = QColor(COLORS["accent_primary"])
            border_color = QColor(255, 255, 255, 120)
        else:
            bg_color = QColor(COLORS["bg_dark_solid"])
            border_color = QColor(255, 255, 255, 45)

        painter.fillPath(path, QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawPath(path)

        # Text & Icon
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🔊 Read")

    def stop(self):
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None
