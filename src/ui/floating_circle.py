import math
import ctypes
from ctypes import wintypes
from typing import Optional
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QRect,
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
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QMenu,
)

from ..config.settings import settings
from ..audio.player import player
from ..audio.tts_engine import tts_engine
from ..audio.voice_manager import voice_manager
from ..capture.text_grabber import text_grabber, window_tracker
from .styles import COLORS
from .black_hole_visualizer import MasterBlackHoleEngine


class FloatingCircleWidget(QWidget):
    """Modern Cosmic Black Hole floating voice controller with sound-reactive accretion

    disk, static pitch-black event horizon, and expandable satellite quick-controls.
    """

    request_snip = pyqtSignal()
    request_settings = pyqtSignal()
    request_hide = pyqtSignal()
    request_close = pyqtSignal()
    clipboard_toggle_changed = pyqtSignal(bool)

    # Satellite definitions: (id, label, angle_radians)
    # "close" is placed directly next to "play_pause" on the orbital ring
    SATELLITES_DEF = [
        ("close",      "Close",      -math.pi * 0.90),
        ("play_pause", "Play/Pause", -math.pi * 0.65),
        ("stop",       "Stop",       -math.pi * 0.40),
        ("snip",       "Snip",       -math.pi * 0.15),
        ("speed",      "Speed",       math.pi * 0.15),
        ("voice",      "Voice",       math.pi * 0.45),
        ("settings",   "Settings",    math.pi * 0.75),
    ]

    def __init__(self):
        super().__init__()

        # Register process ID with window tracker so we never track ourselves as target
        window_tracker.register_own_pid(ctypes.windll.kernel32.GetCurrentProcessId())

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # Dimensions & Geometry
        self.main_radius = 32        # Static 64px diameter Black Hole core
        self.satellite_radius = 18   # 36px diameter satellites
        self.expanded_distance = 78  # Orbital distance of satellites from center
        self.base_width = 260
        self.base_height = 260
        self.resize(self.base_width, self.base_height)
        self.center = QPoint(self.base_width // 2, self.base_height // 2)

        # State
        self.is_expanded = False
        self.expand_progress = 0.0  # 0.0 to 1.0 for smooth animation
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.drag_start_window_pos = QPoint()
        self.has_dragged = False

        # Visualizer & Animation state
        self.current_amplitude = 0.0
        self.smoothed_amplitude = 0.0
        self.pulse_phase = 0.0
        self.anim_time = 0.0
        self.hovered_satellite: Optional[str] = None
        self.hovered_main = False

        # Black Hole Accretion Visualizer Engine
        self.black_hole_engine = MasterBlackHoleEngine(size=self.base_width)
        self.black_hole_engine.set_center(float(self.center.x()), float(self.center.y()))

        # Preparation / Synthesis Progress State
        self.is_preparing = False
        self.target_progress = 0.0
        self.displayed_progress = 0.0
        self.prep_dismiss_timer = 0

        # Setup update timer (60 fps for ultra-smooth cosmic stardust vortex)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_frame)
        self.anim_timer.start(16)

        # Auto collapse timer when mouse leaves
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(1200)
        self.collapse_timer.timeout.connect(self._collapse)

        # Connect audio player and TTS engine callbacks
        player.on_amplitude = self._handle_amplitude
        player.on_state_changed = self._handle_player_state
        tts_engine.on_prepare_progress = self._handle_prepare_progress

        # Restore saved position
        self._restore_position()

    def _restore_position(self):
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        saved_x, saved_y = settings.circle_pos
        if saved_x >= 0 and saved_y >= 0:
            target_x = max(0, min(screen_geo.width() - self.width(), saved_x))
            target_y = max(0, min(screen_geo.height() - self.height(), saved_y))
            self.move(target_x, target_y)
        else:
            default_x = screen_geo.width() - self.width() - 40
            default_y = (screen_geo.height() - self.height()) // 2
            self.move(default_x, default_y)

    def _handle_amplitude(self, amp: float):
        self.current_amplitude = max(0.0, min(1.0, amp))

    def _handle_player_state(self, state: str):
        if state == player.STATE_PLAYING:
            if self.is_preparing:
                self.target_progress = 1.0
                self.displayed_progress = 1.0
        elif state == player.STATE_IDLE:
            self.is_preparing = False
            self.target_progress = 0.0
            self.displayed_progress = 0.0
            self.prep_dismiss_timer = 0
        QTimer.singleShot(0, self.update)

    def _handle_prepare_progress(self, progress: Optional[float]):
        """Receive preparation / synthesis progress from TTS engine."""
        if progress is not None:
            self.is_preparing = True
            self.target_progress = max(self.target_progress, progress)
        else:
            self.is_preparing = False
            self.target_progress = 0.0
            self.displayed_progress = 0.0
            self.prep_dismiss_timer = 0
        QTimer.singleShot(0, self.update)

    def _on_animation_frame(self):
        self.anim_time += 0.016
        self.pulse_phase = (self.pulse_phase + 0.08) % (2.0 * math.pi)

        # Smooth preparation progress interpolation
        if self.is_preparing:
            # While waiting for neural synthesis or model warmup, smoothly advance target_progress up to 88%
            if self.target_progress < 0.88 and player.state != player.STATE_PLAYING:
                self.target_progress += 0.003

            # Smoothly catch up displayed_progress
            self.displayed_progress += (self.target_progress - self.displayed_progress) * 0.22

            # When audio playback starts, lock to 100% and dismiss cleanly
            if player.state == player.STATE_PLAYING:
                self.target_progress = 1.0
                if self.displayed_progress >= 0.96:
                    self.displayed_progress = 1.0
                    self.prep_dismiss_timer += 1
                    if self.prep_dismiss_timer > 6:  # ~100ms display at 100%
                        self.is_preparing = False
                        self.prep_dismiss_timer = 0
            else:
                self.prep_dismiss_timer = 0

        # Amplitude tracking reacting to voice playback
        curr_state = player.state
        if curr_state == player.STATE_PLAYING:
            target_amp = self.current_amplitude
        elif self.is_preparing:
            # Subtle energetic shimmer while preparing
            target_amp = 0.10 + 0.05 * math.sin(self.pulse_phase * 2.0)
        elif curr_state == player.STATE_PAUSED:
            target_amp = 0.08 + 0.04 * math.sin(self.pulse_phase)
        else:
            # Idle gentle cosmic shimmer
            target_amp = 0.03 + 0.02 * math.sin(self.pulse_phase * 0.5)

        self.smoothed_amplitude += (target_amp - self.smoothed_amplitude) * 0.25

        # Update Black Hole accretion vortex (particles, plume, filaments)
        self.black_hole_engine.update(self.smoothed_amplitude, self.anim_time)

        # Smooth expand/collapse progress
        target_progress = 1.0 if self.is_expanded else 0.0
        if abs(self.expand_progress - target_progress) > 0.01:
            self.expand_progress += (target_progress - self.expand_progress) * 0.2

        self.update()

    def _collapse(self):
        self.is_expanded = False
        self.update()

    # --- Mouse & Interaction Events ---

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            WM_MOUSEACTIVATE = 0x0021
            MA_NOACTIVATE = 3
            if msg.message == WM_MOUSEACTIVATE:
                # Do not activate window or steal focus from active document on click
                return True, MA_NOACTIVATE
        return False, 0

    def enterEvent(self, event):
        window_tracker.record_foreground()
        self.hovered_main = True
        self.is_expanded = True
        self.collapse_timer.stop()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered_main = False
        self.hovered_satellite = None
        self.collapse_timer.start()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        window_tracker.record_foreground()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.has_dragged = False
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_window_pos = self.pos()
            self.collapse_timer.stop()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            if delta.manhattanLength() > 5:
                self.has_dragged = True
                self.move(self.drag_start_window_pos + delta)
            event.accept()
            return

        # Check satellite hovering
        sat = self._get_satellite_at_pos(pos)
        if sat != self.hovered_satellite:
            self.hovered_satellite = sat
            self.update()

        # Check main black hole core hovering
        dist_to_center = math.hypot(pos.x() - self.center.x(), pos.y() - self.center.y())
        hovered = dist_to_center <= self.main_radius + 4
        if hovered != self.hovered_main:
            self.hovered_main = hovered
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            if self.has_dragged:
                # Snap to edge if within 30px
                self._snap_to_edge()
                settings.set_circle_pos(self.x(), self.y())
                event.accept()
                return

            # Clicked on satellite or main black hole circle
            pos = event.position().toPoint()
            clicked_sat = self._get_satellite_at_pos(pos)
            if clicked_sat:
                self._handle_satellite_click(clicked_sat)
            elif math.hypot(pos.x() - self.center.x(), pos.y() - self.center.y()) <= self.main_radius + 4:
                self._handle_main_circle_click()

            event.accept()

    def _snap_to_edge(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x, y = self.x(), self.y()

        # Left/Right snap
        if x < geo.left() + 30:
            x = geo.left() - 20
        elif x + self.width() > geo.right() - 30:
            x = geo.right() - self.width() + 20

        # Top/Bottom boundary constraints
        y = max(geo.top(), min(geo.bottom() - self.height(), y))
        self.move(x, y)

    def _handle_main_circle_click(self):
        """Action when clicking the central circle:

        - If currently playing: pause.
        - If paused: resume.
        - If idle: grab selected text and read immediately!
        """
        curr_state = player.state
        if curr_state == player.STATE_PLAYING:
            player.pause()
        elif curr_state == player.STATE_PAUSED:
            player.resume()
        else:
            self.read_selected_text()

    def read_selected_text(self):
        """Grab selected text from active window and speak aloud."""
        # Immediately display preparation state for instant 0ms visual feedback
        self.is_preparing = True
        self.displayed_progress = 0.0
        self.target_progress = 0.08
        self.update()

        text = text_grabber.get_selected_text(
            restore_clipboard=settings.get("restore_clipboard_after_read", True)
        )
        if text and text.strip():
            print(f"[ReadAloud] Reading {len(text.strip())} chars: {text.strip()[:60]}...")
            tts_engine.speak(text.strip())
        else:
            print("[ReadAloud] No text was selected in foreground window.")
            self.is_preparing = False
            self.update()

    def _handle_satellite_click(self, sat_id: str):
        if sat_id == "close":
            self.request_close.emit()
        elif sat_id == "play_pause":
            player.toggle_play_pause()
        elif sat_id == "stop":
            tts_engine.stop()
        elif sat_id == "snip":
            self.request_snip.emit()
        elif sat_id == "speed":
            self._cycle_speed()
        elif sat_id == "voice":
            self._cycle_voice()
        elif sat_id == "settings":
            self.request_settings.emit()
        elif sat_id == "hide":
            self.request_hide.emit()

    def _cycle_speed(self):
        speeds = [0.8, 1.0, 1.25, 1.5, 2.0]
        curr = settings.speed
        next_speed = speeds[0]
        for s in speeds:
            if s > curr + 0.05:
                next_speed = s
                break
        settings.speed = next_speed
        self.update()

    def _cycle_voice(self):
        voices = voice_manager.get_voices()
        curr_id = settings.voice
        next_voice = voices[0].id
        for i, v in enumerate(voices):
            if v.id == curr_id and i + 1 < len(voices):
                next_voice = voices[i + 1].id
                break
        settings.voice = next_voice
        self.update()

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {COLORS['bg_dark_solid']}; color: #ffffff; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 6px; }}"
            f"QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}"
            f"QMenu::item:selected {{ background-color: {COLORS['accent_primary']}; }}"
        )

        read_action = menu.addAction("🔊 Read Selected Text (Ctrl+Alt+R)")
        read_action.triggered.connect(self.read_selected_text)

        snip_action = menu.addAction("✂ Snip & Read Screen (Ctrl+Alt+S)")
        snip_action.triggered.connect(self.request_snip.emit)

        menu.addSeparator()

        if player.state == player.STATE_PLAYING:
            pause_action = menu.addAction("⏸ Pause")
            pause_action.triggered.connect(player.pause)
        elif player.state == player.STATE_PAUSED:
            resume_action = menu.addAction("▶ Resume")
            resume_action.triggered.connect(player.resume)

        menu.addSeparator()

        auto_read_action = menu.addAction("📋 Auto-Read Copied Text (Ctrl+C)")
        auto_read_action.setCheckable(True)
        auto_read_action.setChecked(settings.get("auto_read_clipboard", False))
        auto_read_action.toggled.connect(self._toggle_auto_read)

        menu.addSeparator()

        settings_action = menu.addAction("⚙ Settings")
        settings_action.triggered.connect(self.request_settings.emit)

        hide_action = menu.addAction("👁 Hide to System Tray")
        hide_action.triggered.connect(self.request_hide.emit)

        menu.exec(global_pos)

    def _toggle_auto_read(self, enabled: bool):
        settings.set("auto_read_clipboard", enabled)
        self.clipboard_toggle_changed.emit(enabled)

    # --- Satellite Positions & Layout ---

    def _get_satellites_def(self):
        """Return satellite definitions, with live speed label for display."""
        result = []
        for sat_id, label, angle in self.SATELLITES_DEF:
            if sat_id == "speed":
                result.append((sat_id, f"{settings.speed}x", angle))
            else:
                result.append((sat_id, label, angle))
        return result

    def _get_satellite_rect(self, angle: float) -> QRect:
        dist = self.expanded_distance * self.expand_progress
        cx = self.center.x() + int(math.cos(angle) * dist)
        cy = self.center.y() + int(math.sin(angle) * dist)
        r = int(self.satellite_radius * self.expand_progress)
        return QRect(cx - r, cy - r, r * 2, r * 2)

    def _get_satellite_at_pos(self, pos: QPoint) -> Optional[str]:
        if self.expand_progress < 0.3:
            return None
        for sat_id, _, angle in self._get_satellites_def():
            rect = self._get_satellite_rect(angle)
            if rect.contains(pos):
                return sat_id
        return None

    # --- Custom Painting & Black Hole Aesthetics ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        curr_state = player.state

        # 1. Render Colorful Accretion Disk (Nebulae, Photon Rings, Filaments, Stardust)
        # Changes dynamically based on sound/voice amplitude!
        self.black_hole_engine.render_accretion_disk(
            painter, self.smoothed_amplitude, self.anim_time
        )

        # 2. Render Satellite Quick Controls (if expanded on hover)
        if self.expand_progress > 0.05:
            self._paint_satellites(painter)

        # 3. Render Central Static Black Hole (The Singularity / Event Horizon)
        # As requested: "is the Blackhole in the middle stay static but the surround
        # colorful start to change based on the sound that created by the voice"
        # Shows dynamic white percentage in the center ONLY when preparing text to read!
        self.black_hole_engine.render_static_black_hole(
            painter,
            radius=float(self.main_radius),
            is_hovered=self.hovered_main,
            is_paused=(curr_state == player.STATE_PAUSED),
            is_playing=(curr_state == player.STATE_PLAYING),
            prepare_progress=(self.displayed_progress if self.is_preparing else None),
        )

    def _paint_satellites(self, painter: QPainter):
        for sat_id, label, angle in self._get_satellites_def():
            rect = self._get_satellite_rect(angle)
            if rect.width() <= 4:
                continue

            is_hovered = self.hovered_satellite == sat_id

            # Glow aura on hover
            if is_hovered:
                glow_path = QPainterPath()
                glow_path.addEllipse(QRectF(rect).adjusted(-3, -3, 3, 3))
                glow_color = (
                    QColor(239, 68, 68, 140)  # Rose red glow for close
                    if sat_id == "close"
                    else QColor(0, 220, 255, 120)
                )
                painter.fillPath(glow_path, glow_color)

            # Border
            if is_hovered:
                border_color = (
                    QColor(254, 202, 202, int(255 * self.expand_progress))
                    if sat_id == "close"
                    else QColor(0, 240, 255, int(240 * self.expand_progress))
                )
            else:
                border_color = QColor(255, 255, 255, int(70 * self.expand_progress))
            border_pen = QPen(border_color, 1.5)

            # Satellite Circle Background (Frosted Cosmic Obsidian Glass)
            if is_hovered:
                bg_color = (
                    QColor(220, 38, 38, int(245 * self.expand_progress))
                    if sat_id == "close"
                    else QColor(0, 180, 240, int(245 * self.expand_progress))
                )
                text_color = (
                    QColor(255, 255, 255, int(255 * self.expand_progress))
                    if sat_id == "close"
                    else QColor(0, 0, 0, int(255 * self.expand_progress))
                )
            else:
                bg_color = QColor(14, 18, 28, int(235 * self.expand_progress))
                text_color = QColor(255, 255, 255, int(255 * self.expand_progress))

            painter.setPen(border_pen)
            painter.setBrush(QBrush(bg_color))
            painter.drawEllipse(rect)

            # Icon / Label inside satellite
            painter.setPen(text_color)
            font = QFont("Segoe UI", 9, QFont.Weight.Bold if is_hovered else QFont.Weight.DemiBold)
            painter.setFont(font)

            if sat_id == "close":
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "✕")
            elif sat_id == "play_pause":
                icon_text = "⏸" if player.state == player.STATE_PLAYING else "▶"
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, icon_text)
            elif sat_id == "stop":
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "⏹")
            elif sat_id == "snip":
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "✂")
            elif sat_id == "speed":
                speed_str = f"{settings.speed}x"
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, speed_str)
            elif sat_id == "voice":
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🗣")
            elif sat_id == "settings":
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "⚙")
