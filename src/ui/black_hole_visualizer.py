import math
import random
from typing import Dict, List, Tuple, Optional
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QRadialGradient,
    QConicalGradient,
    QPainterPath,
    QFont,
)


class StardustMist:
    """Individual micro-stardust grain orbiting the black hole with Keplerian speed

    and sound-reactive radial excitation.
    """
    __slots__ = (
        "r_base",
        "r",
        "angle",
        "orbit_speed",
        "radial_drift",
        "size",
        "base_alpha",
        "color_type",
        "is_plume",
        "jitter",
    )

    def __init__(self, r_min: float = 32.2, r_max: float = 125.0):
        # 3 Populations matching the reference image:
        # 1. Top-Left Relativistic Plume (~10:30 o'clock: 3.55 to 4.25 rad) - 30% of particles
        # 2. Dense Inner Accretion Cloud (32.2 to 58.0) - 50% of particles
        # 3. Outer Diffuse Spray (58.0 to 115.0) - 20% of particles
        roll = random.random()
        self.is_plume = (roll < 0.30)

        if self.is_plume:
            # Concentrated plume cone towards top-left (approx -135° +/- 22°)
            self.angle = random.uniform(3.55, 4.25)
            # Long plume spray reaching far out into space
            self.r_base = r_min + (random.random() ** 1.1) * 88.0
        elif roll < 0.80:
            # Inner dense accretion donut cloud
            self.angle = random.uniform(0.0, 2.0 * math.pi)
            self.r_base = r_min + (random.random() ** 1.4) * 26.0
        else:
            # Outer diffuse spray
            self.angle = random.uniform(0.0, 2.0 * math.pi)
            self.r_base = r_min + 22.0 + (random.random() ** 1.2) * (r_max - r_min - 22.0)

        self.r = self.r_base
        # Keplerian differential rotation: inner orbits faster
        kepler = (33.0 / max(22.0, self.r_base)) ** 0.85
        self.orbit_speed = 0.015 * kepler * random.uniform(0.75, 1.25)
        self.radial_drift = random.uniform(0.7, 1.8)

        # Fine micro stardust sizes (0.6px to 1.7px, with 3.5% larger star gems)
        if random.random() < 0.035:
            self.size = random.uniform(2.0, 2.6)
        else:
            self.size = random.uniform(0.65, 1.55)

        self.base_alpha = random.randint(140, 255)
        self.jitter = random.uniform(0.0, 2.0 * math.pi)
        self._assign_color()

    def _assign_color(self):
        norm_a = self.angle % (2.0 * math.pi)
        # In screen coords:
        # 0 is Right (+X) -> Warm Gold / Amber
        # pi/2 is Down (+Y) -> Electric Cyan / Azure
        # pi is Left (-X) -> Electric Cyan
        # Plume is ~3.55 - 4.25 rad (Top-Left) -> Electric Cyan + White Stardust
        # 3pi/2 is Up (-Y) -> Transition to Gold
        if self.is_plume:
            r = random.random()
            if r < 0.38:
                self.color_type = "spark_white"
            elif r < 0.78:
                self.color_type = "neon_cyan"
            else:
                self.color_type = "ice_blue"
        elif 1.75 < norm_a < 4.85:
            r = random.random()
            if r < 0.12:
                self.color_type = "spark_white"
            elif r < 0.65:
                self.color_type = "neon_cyan"
            elif r < 0.88:
                self.color_type = "ice_blue"
            else:
                self.color_type = "deep_cyan"
        else:
            r = random.random()
            if r < 0.12:
                self.color_type = "spark_gold"
            elif r < 0.65:
                self.color_type = "amber_gold"
            elif r < 0.88:
                self.color_type = "copper_orange"
            else:
                self.color_type = "fiery_ember"


class AccretionFilament:
    """Subtle relativistic filaments and curved streamlines radiating from the accretion disk."""
    __slots__ = ("angle", "r_start", "r_len", "curve", "width", "alpha", "is_cyan", "is_plume")

    def __init__(self, r_min: float = 32.2):
        self.angle = random.uniform(0.0, 2.0 * math.pi)
        norm_a = self.angle % (2.0 * math.pi)
        self.is_plume = (3.55 < norm_a < 4.25)
        self.is_cyan = (1.75 < norm_a < 4.85) or self.is_plume

        self.r_start = r_min + random.uniform(0.5, 4.0)
        plume_mult = 2.2 if self.is_plume else 1.0
        self.r_len = random.uniform(12.0, 32.0) * plume_mult
        self.curve = random.uniform(-0.12, 0.20)
        self.width = random.uniform(0.5, 0.9) * (1.15 if self.is_plume else 0.85)
        self.alpha = random.randint(50, 160)


class MasterBlackHoleEngine:
    """Cosmic Black Hole Accretion Engine with sound-reactive stardust vortex,

    lensing photon rings, relativistic jet plume, and a static event horizon.
    """

    def __init__(self, size: int = 260):
        self.size = float(size)
        self.cx = self.size / 2.0
        self.cy = self.size / 2.0
        self.bh_radius = 32.0  # Center stays completely static!

        # 950 micro stardust particles for dense, breathtaking cosmic sand at 120+ FPS
        self.num_particles = 950
        self.particles: List[StardustMist] = [
            StardustMist(r_min=32.2, r_max=125.0) for _ in range(self.num_particles)
        ]

        # 60 fine wispy filaments
        self.filaments: List[AccretionFilament] = [
            AccretionFilament(r_min=32.2) for _ in range(60)
        ]

        # Concentric photon rings hugging the event horizon
        self.photon_ring_radii: List[Tuple[float, float, int]] = [
            (32.6, 1.8, 255),
            (33.8, 1.5, 235),
            (35.2, 1.3, 210),
            (36.8, 1.1, 180),
            (38.6, 1.0, 150),
            (40.6, 0.9, 120),
            (42.8, 0.8, 90),
        ]

        self.palette: Dict[str, QColor] = {
            "spark_white": QColor(245, 255, 255),
            "neon_cyan": QColor(0, 245, 255),
            "ice_blue": QColor(115, 230, 255),
            "deep_cyan": QColor(0, 175, 245),
            "spark_gold": QColor(255, 250, 230),
            "amber_gold": QColor(255, 195, 45),
            "copper_orange": QColor(255, 145, 25),
            "fiery_ember": QColor(255, 95, 15),
        }

    def set_center(self, cx: float, cy: float):
        self.cx = cx
        self.cy = cy

    def update(self, amp: float, time_val: float):
        """Update particle orbits, radial flare, and audio excitement."""
        for p in self.particles:
            # Voice speedup: vortex accelerates when speaking
            angular_boost = p.orbit_speed * (1.0 + amp * 2.8)
            p.angle = (p.angle + angular_boost) % (2.0 * math.pi)

            # Voice radial flare: stardust sprays outward
            flare = amp * 25.0 * p.radial_drift
            if p.is_plume:
                flare = amp * 56.0 * p.radial_drift

            turb = math.sin(time_val * 4.2 + p.jitter) * (0.8 + amp * 2.8)
            p.r = p.r_base + flare + turb
            p._assign_color()

        for f in self.filaments:
            f.angle = (f.angle + 0.007 * (1.0 + amp * 2.2)) % (2.0 * math.pi)

    def render_accretion_disk(self, painter: QPainter, amp: float, time_val: float):
        """Render the surrounding colorful accretion disk, photon rings, and stardust particles.

        All of these elements react dynamically to the live voice amplitude.
        """
        cx, cy = self.cx, self.cy

        # ----------------------------------------------------
        # 1. Glowing Accretion Nebulae (Soft light beneath particles)
        # ----------------------------------------------------
        # Cyan aura (lower-left & top-left plume)
        c_glow = QRadialGradient(cx - 16.0 - amp * 8.0, cy + 6.0 + amp * 6.0, 75.0 + amp * 36.0)
        c_alpha = int(75 + amp * 145)
        c_glow.setColorAt(0.0, QColor(0, 230, 255, c_alpha))
        c_glow.setColorAt(0.35, QColor(0, 160, 255, int(c_alpha * 0.55)))
        c_glow.setColorAt(0.75, QColor(2, 60, 180, int(c_alpha * 0.12)))
        c_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(c_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 115.0 + amp * 18.0, 115.0 + amp * 18.0)

        # Gold aura (upper-right)
        g_glow = QRadialGradient(cx + 16.0 + amp * 8.0, cy - 8.0 - amp * 6.0, 70.0 + amp * 36.0)
        g_alpha = int(75 + amp * 145)
        g_glow.setColorAt(0.0, QColor(255, 175, 35, g_alpha))
        g_glow.setColorAt(0.35, QColor(255, 115, 15, int(g_alpha * 0.55)))
        g_glow.setColorAt(0.75, QColor(190, 45, 5, int(g_alpha * 0.12)))
        g_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(g_glow))
        painter.drawEllipse(QPointF(cx, cy), 110.0 + amp * 18.0, 110.0 + amp * 18.0)

        # ----------------------------------------------------
        # 2. Relativistic Curved Filaments (Subtle wisps)
        # ----------------------------------------------------
        for f in self.filaments:
            alpha = int(f.alpha * (0.5 + amp * 0.85))
            if f.is_plume:
                alpha = min(255, int(alpha * 1.35))
            alpha = max(15, min(255, alpha))

            if f.is_plume:
                color = QColor(220, 250, 255, alpha)
            elif f.is_cyan:
                color = QColor(0, 230, 255, alpha)
            else:
                color = QColor(255, 180, 50, alpha)

            pen = QPen(color, f.width * (1.1 if f.is_plume else 0.85))
            painter.setPen(pen)

            path = QPainterPath()
            steps = 6
            cur_len = f.r_len + (amp * 32.0 if f.is_plume else amp * 16.0)
            dr = cur_len / steps
            for st in range(steps + 1):
                cur_r = f.r_start + st * dr
                cur_a = f.angle + (st * dr) * 0.016 * f.curve
                px = cx + math.cos(cur_a) * cur_r
                py = cy + math.sin(cur_a) * cur_r
                if st == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.drawPath(path)

        # ----------------------------------------------------
        # 3. Concentric Photon Rings (Continuous 360° Conical Gradient Orbits)
        # ----------------------------------------------------
        conic = QConicalGradient(cx, cy, 35.0)
        conic.setColorAt(0.0, QColor(255, 195, 45))    # Right: Gold
        conic.setColorAt(0.20, QColor(255, 140, 20))   # Bottom-right: Amber
        conic.setColorAt(0.38, QColor(0, 200, 255))    # Bottom-left: Azure
        conic.setColorAt(0.55, QColor(0, 245, 255))    # Left: Electric Cyan
        conic.setColorAt(0.72, QColor(140, 235, 255))  # Top-left: Ice Cyan
        conic.setColorAt(0.85, QColor(255, 215, 60))   # Top: Warm Gold
        conic.setColorAt(1.0, QColor(255, 195, 45))    # Right: Gold

        for r_ring, pen_w, base_a in self.photon_ring_radii:
            alpha = int(base_a * (0.65 + amp * 0.75))
            alpha = max(25, min(255, alpha))

            ring_pen = QPen(QBrush(conic), pen_w)
            painter.save()
            painter.setOpacity(alpha / 255.0)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r_ring, r_ring)
            painter.restore()

        # ----------------------------------------------------
        # 4. Dense Stardust Mist (Micro Particles)
        # ----------------------------------------------------
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            px = cx + math.cos(p.angle) * p.r
            py = cy + math.sin(p.angle) * p.r

            base_col = self.palette[p.color_type]
            dist_norm = max(0.12, 1.0 - (p.r - self.bh_radius) / 92.0)
            p_alpha = int((p.base_alpha * (0.6 + amp * 0.8)) * dist_norm)
            p_alpha = max(20, min(255, p_alpha))

            draw_col = QColor(base_col.red(), base_col.green(), base_col.blue(), p_alpha)

            # Stardust point
            painter.setBrush(QBrush(draw_col))
            sz = p.size * (1.0 + amp * 0.25)
            painter.drawEllipse(QPointF(px, py), sz / 2.0, sz / 2.0)

            # Tiny soft halo for prominent stars
            if p.size > 2.0:
                glow_col = QColor(base_col.red(), base_col.green(), base_col.blue(), int(p_alpha * 0.35))
                painter.setBrush(QBrush(glow_col))
                painter.drawEllipse(QPointF(px, py), sz * 1.4, sz * 1.4)

    def render_static_black_hole(
        self,
        painter: QPainter,
        radius: float,
        is_hovered: bool = False,
        is_paused: bool = False,
        is_playing: bool = False,
        prepare_progress: Optional[float] = None,
    ):
        """Render the static central Black Hole (The Singularity & Event Horizon).

        As requested by user: the central Blackhole stays static, circular, and pitch-black,
        drawn solidly on top of inner swirls to anchor the celestial visual.
        When text is preparing/synthesizing, displays dynamic white percentage (0% to 100%).
        """
        cx, cy = self.cx, self.cy

        # 1. Pitch-Black Core (Absolute void / Event horizon)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 255)))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # 2. Razor-sharp Event Horizon Rim
        rim_pen = QPen(QColor(15, 18, 25, 245), 1.0)
        painter.setPen(rim_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # 3. State & Progress inside the static black hole:
        if prepare_progress is not None:
            # Dynamic synthesis preparation percentage in center of Black Hole
            # Displayed in crisp white text right in the middle
            pct = min(100, max(0, int(prepare_progress * 100)))
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font)
            rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{pct}%")

        elif is_paused:
            # Subtle glowing pause bars inside core
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(245, 158, 11, 220)))  # Amber pause
            painter.drawRoundedRect(QRectF(cx - 7.0, cy - 8.0, 4.5, 16.0), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(cx + 2.5, cy - 8.0, 4.5, 16.0), 1.5, 1.5)

        elif not is_playing and is_hovered:
            # Idle hover: subtle crisp speaker / sound glyph inviting user to click to read
            painter.setPen(QColor(255, 255, 255, 210))
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🔊")
