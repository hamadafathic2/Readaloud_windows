import threading
import io
from typing import Optional
import numpy as np
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QBuffer, QIODevice, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QCursor,
    QPixmap,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QFont,
    QPainterPath,
)
from PyQt6.QtWidgets import QWidget, QApplication
from PIL import Image

from ..capture.ocr_engine import ocr_engine
from ..audio.tts_engine import tts_engine
from .styles import COLORS


class SnipOverlay(QWidget):
    """Fullscreen screen snipping overlay to select any text area for instant OCR.
    
    Fully DPI-aware: renders exact 1:1 screen pixels with zero zoom in or out.
    """

    snip_completed = pyqtSignal(str)
    snip_no_text = pyqtSignal()
    snip_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMouseTracking(True)

        self.screen_pixmap: Optional[QPixmap] = None
        self.dpr: float = 1.0
        self.start_point: Optional[QPoint] = None
        self.current_point: Optional[QPoint] = None
        self.is_selecting = False

    def start_snip(self):
        """Capture screen at 1:1 scale and display snipping overlay without zoom."""
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        if not screen:
            return

        self.dpr = screen.devicePixelRatio()
        geo = screen.geometry()

        # Capture the entire screen in physical resolution
        self.screen_pixmap = screen.grabWindow(0)
        # Match pixmap device pixel ratio to screen DPR for 1:1 pixel rendering
        self.screen_pixmap.setDevicePixelRatio(self.dpr)

        self.setGeometry(geo)
        self.start_point = None
        self.current_point = None
        self.is_selecting = False

        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.snip_finished.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.position().toPoint()
            self.current_point = self.start_point
            self.is_selecting = True
            self.update()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click cancels snipping
            self.close()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.current_point = event.position().toPoint()
        if self.is_selecting:
            self.update()
            event.accept()
        else:
            # Update to draw crosshair guides if desired
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.current_point = event.position().toPoint()
            rect = self._get_selection_rect()

            self.close()

            # Process selection if valid size (at least 4x4 logical px)
            if rect.width() >= 4 and rect.height() >= 4 and self.screen_pixmap:
                img = self.screen_pixmap.toImage()

                # Convert logical rectangle coordinates to physical image pixels
                phys_x = int(round(rect.x() * self.dpr))
                phys_y = int(round(rect.y() * self.dpr))
                phys_w = int(round(rect.width() * self.dpr))
                phys_h = int(round(rect.height() * self.dpr))

                # Clamp within image bounds
                phys_x = max(0, min(phys_x, img.width() - 1))
                phys_y = max(0, min(phys_y, img.height() - 1))
                phys_w = max(1, min(phys_w, img.width() - phys_x))
                phys_h = max(1, min(phys_h, img.height() - phys_y))

                cropped_image = img.copy(phys_x, phys_y, phys_w, phys_h)
                # Convert directly to RGB888 numpy array (zero buffer/disk overhead)
                img_rgb = cropped_image.convertToFormat(QImage.Format.Format_RGB888)
                w, h = img_rgb.width(), img_rgb.height()
                bpl = img_rgb.bytesPerLine()
                ptr = img_rgb.bits()
                ptr.setsize(h * bpl)
                arr = (
                    np.frombuffer(ptr, np.uint8)
                    .reshape((h, bpl))[:, : w * 3]
                    .reshape((h, w, 3))
                    .copy()
                )

                threading.Thread(
                    target=self._process_cropped_image,
                    args=(arr,),
                    daemon=True,
                ).start()

            event.accept()

    def _get_selection_rect(self) -> QRect:
        if not self.start_point or not self.current_point:
            return QRect()
        x1 = min(self.start_point.x(), self.current_point.x())
        y1 = min(self.start_point.y(), self.current_point.y())
        x2 = max(self.start_point.x(), self.current_point.x())
        y2 = max(self.start_point.y(), self.current_point.y())
        return QRect(x1, y1, x2 - x1, y2 - y1)

    def _process_cropped_image(self, img_array: np.ndarray):
        """Run multi-pass RapidOCR on cropped image array and synthesize speech."""
        try:
            extracted_text = ocr_engine.extract_text(img_array)
            print(f"[SnipOverlay] Extracted {len(extracted_text)} characters via OCR.")

            if extracted_text and extracted_text.strip():
                self.snip_completed.emit(extracted_text.strip())
                tts_engine.speak(extracted_text.strip())
            else:
                print("[SnipOverlay] No text was detected in the snipped region.")
                self.snip_no_text.emit()
        except Exception as e:
            print(f"[SnipOverlay] Error processing cropped image: {e}")
            self.snip_no_text.emit()

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1. Draw full frozen desktop screenshot at exact 1:1 scale (zero zoom)
        if self.screen_pixmap:
            painter.drawPixmap(0, 0, self.screen_pixmap)

        # 2. Dim the entire screen with semi-transparent mask, cutting a hole for selection
        rect = self._get_selection_rect()
        mask_path = QPainterPath()
        mask_path.addRect(QRectF(self.rect()))

        if not rect.isEmpty():
            mask_path.addRect(QRectF(rect))

        mask_path.setFillRule(Qt.FillRule.OddEvenFill)
        painter.fillPath(mask_path, QColor(0, 0, 0, 115))

        # 3. Highlight selection rectangle
        if not rect.isEmpty():
            # Border around selection
            pen = QPen(QColor(COLORS["accent_primary"]), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            # Dimensions badge below selection
            dim_text = f"{rect.width()} × {rect.height()} px"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#ffffff"))
            badge_y = rect.bottom() + 6 if rect.bottom() + 30 < self.height() else rect.top() - 26
            badge_rect = QRect(rect.left(), badge_y, 110, 22)
            painter.fillRect(badge_rect, QColor(20, 24, 33, 220))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, dim_text)

        # 4. Top instruction banner
        banner_w = 420
        banner_h = 36
        banner_x = (self.width() - banner_w) // 2
        banner_y = 28
        banner_rect = QRect(banner_x, banner_y, banner_w, banner_h)

        painter.setBrush(QBrush(QColor(20, 24, 33, 230)))
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.drawRoundedRect(banner_rect, 18, 18)

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            banner_rect,
            Qt.AlignmentFlag.AlignCenter,
            "Drag around any text to read aloud  •  ESC to cancel",
        )
