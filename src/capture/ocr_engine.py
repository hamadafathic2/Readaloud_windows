import re
from typing import Optional, Union, List, Dict, Any
import numpy as np
from PIL import Image, ImageOps

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None


class OCREngine:
    """Fast, local, offline OCR engine using RapidOCR ONNX with intelligent multi-pass

    preprocessing, border padding, small-font upscaling, and natural reading-order sorting.
    """

    def __init__(self):
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None and RapidOCR is not None:
            try:
                self._ocr = RapidOCR()
            except Exception as e:
                print(f"[OCREngine] Error initializing RapidOCR: {e}")
        return self._ocr

    def extract_text(self, image_input: Union[Image.Image, np.ndarray]) -> str:
        """Extract text from an image or screenshot array with multi-pass robustness."""
        ocr = self._get_ocr()
        if ocr is None:
            print("[OCREngine] RapidOCR not available.")
            return ""

        # 1. Convert to PIL Image and normalize transparency
        if isinstance(image_input, np.ndarray):
            img = Image.fromarray(image_input)
        else:
            img = image_input

        # Composite any alpha onto white so transparent backgrounds never turn black
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

        # 2. Multi-pass OCR pipeline
        # Pass 1: Original with border padding (and 2x scale if small font)
        padded_img = self._prepare_image_with_padding(img)
        text = self._run_ocr_pass(ocr, padded_img, box_thresh=0.25, text_score=0.25)
        if text.strip():
            return self._clean_ocr_text(text)

        # Pass 2: Grayscale with autocontrast (handles low-contrast / washed-out text)
        gray_img = ImageOps.autocontrast(ImageOps.grayscale(padded_img)).convert("RGB")
        text = self._run_ocr_pass(ocr, gray_img, box_thresh=0.2, text_score=0.2)
        if text.strip():
            return self._clean_ocr_text(text)

        # Pass 3: Inverted colors (handles dark mode / white text on dark backgrounds)
        inverted_img = ImageOps.invert(gray_img)
        text = self._run_ocr_pass(ocr, inverted_img, box_thresh=0.2, text_score=0.2)
        if text.strip():
            return self._clean_ocr_text(text)

        # Pass 4: Direct recognition without DBNet detection (for isolated single words, tight crops, buttons)
        text = self._run_direct_rec_pass(ocr, padded_img)
        if text.strip():
            return self._clean_ocr_text(text)

        # Pass 5: Direct recognition on inverted image (dark mode single words)
        text = self._run_direct_rec_pass(ocr, inverted_img)
        if text.strip():
            return self._clean_ocr_text(text)

        return ""

    def _prepare_image_with_padding(self, source_img: Image.Image, pad: int = 18) -> Image.Image:
        """Upscale small text if needed and add border padding matching average edge color.
        
        Text detection models (DBNet) fail when letters touch image edges. Adding padding
        matching the background color guarantees high detection confidence.
        """
        w, h = source_img.size

        # If image is small or single/double line of text, upscale 2x for clearer character features
        if h < 120 or w < 240:
            scale = 2.0
            source_img = source_img.resize(
                (int(w * scale), int(h * scale)), Image.Resampling.LANCZOS
            )
            w, h = source_img.size

        # Sample border pixels to compute average edge background color
        edge_pixels = []
        for x in (0, w - 1):
            for y in range(0, h, max(1, h // 6)):
                edge_pixels.append(source_img.getpixel((x, y)))
        for y in (0, h - 1):
            for x in range(0, w, max(1, w // 6)):
                edge_pixels.append(source_img.getpixel((x, y)))

        if edge_pixels:
            avg_r = int(sum(p[0] for p in edge_pixels) / len(edge_pixels))
            avg_g = int(sum(p[1] for p in edge_pixels) / len(edge_pixels))
            avg_b = int(sum(p[2] for p in edge_pixels) / len(edge_pixels))
            edge_color = (avg_r, avg_g, avg_b)
        else:
            edge_color = (255, 255, 255)

        padded = Image.new("RGB", (w + pad * 2, h + pad * 2), color=edge_color)
        padded.paste(source_img, (pad, pad))
        return padded

    def _run_ocr_pass(
        self,
        ocr,
        target_img: Image.Image,
        box_thresh: float = 0.25,
        text_score: float = 0.25,
    ) -> str:
        """Run RapidOCR on image and sort boxes in human reading order."""
        try:
            res, _ = ocr(
                np.array(target_img),
                box_thresh=box_thresh,
                text_score=text_score,
                unclip_ratio=1.6,
            )
            if not res:
                return ""

            boxes: List[Dict[str, Any]] = []
            for item in res:
                if not item or len(item) < 2 or not item[1].strip():
                    continue
                box = item[0]
                text = item[1].strip()
                # Compute vertical center, left X, and height
                y_center = (box[0][1] + box[2][1]) / 2.0
                x_left = min(p[0] for p in box)
                h = max(p[1] for p in box) - min(p[1] for p in box)
                boxes.append({
                    "text": text,
                    "y": y_center,
                    "x": x_left,
                    "h": max(h, 12),
                })

            if not boxes:
                return ""

            # Sort top to bottom
            boxes.sort(key=lambda b: b["y"])

            # Group into lines based on vertical proximity
            lines = []
            curr_line = [boxes[0]]
            for b in boxes[1:]:
                avg_h = sum(it["h"] for it in curr_line) / len(curr_line)
                if abs(b["y"] - curr_line[-1]["y"]) < avg_h * 0.65:
                    curr_line.append(b)
                else:
                    curr_line.sort(key=lambda it: it["x"])
                    lines.append(" ".join(it["text"] for it in curr_line))
                    curr_line = [b]

            if curr_line:
                curr_line.sort(key=lambda it: it["x"])
                lines.append(" ".join(it["text"] for it in curr_line))

            return "\n".join(lines)
        except Exception as e:
            print(f"[OCREngine] OCR pass error: {e}")
            return ""

    def _run_direct_rec_pass(self, ocr, target_img: Image.Image) -> str:
        """Run text recognizer directly on image without DBNet detection for small crops."""
        try:
            res, _ = ocr(np.array(target_img), use_text_det=False)
            if not res:
                return ""
            texts = [
                item[1].strip()
                for item in res
                if item and len(item) >= 2 and item[1].strip()
            ]
            return " ".join(texts)
        except Exception as e:
            print(f"[OCREngine] Direct rec pass error: {e}")
            return ""

    @staticmethod
    def _clean_ocr_text(text: str) -> str:
        """Clean OCR output: join hyphenated line breaks, consolidate paragraphs, and remove junk."""
        # Join words broken by hyphens at end of line (e.g. "connec-\ntion" -> "connection")
        text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
        # Consolidate line breaks that are continuation of the same sentence
        lines = text.split("\n")
        joined = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if joined and not joined[-1].endswith((".", "!", "?", ":", ";")):
                joined[-1] += " " + line
            else:
                joined.append(line)
        cleaned = "\n".join(joined).strip()
        # Remove repeated non-alphanumeric noise strips (e.g. "------" or "_____")
        cleaned = re.sub(r"[-_=~*#]{3,}", " ", cleaned)
        return cleaned.strip()


ocr_engine = OCREngine()
