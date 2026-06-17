"""OCR Parser using EasyOCR with pytesseract fallback.

Pipeline: Image File → EasyOCR Reader → Raw OCR Text → Post-Processing → Structured Data
"""
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    raw_text: str
    confidence: float
    lines: list[str] = field(default_factory=list)
    source_engine: str = "unknown"


class OCRParser:
    """Multi-engine OCR parser with EasyOCR primary and pytesseract fallback."""

    def __init__(self, languages: list[str] = None):
        self.languages = languages or ["en"]
        self._reader = None

    def _get_easyocr_reader(self):
        if self._reader is None and EASYOCR_AVAILABLE:
            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def parse_image(self, image_path: str) -> OCRResult:
        """Extract text from image using EasyOCR with pytesseract fallback."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Try EasyOCR first
        if EASYOCR_AVAILABLE:
            return self._parse_with_easyocr(image_path)

        # Fallback to pytesseract
        if TESSERACT_AVAILABLE:
            return self._parse_with_tesseract(image_path)

        raise RuntimeError("No OCR engine available. Install easyocr or pytesseract.")

    def _parse_with_easyocr(self, image_path: str) -> OCRResult:
        """Parse image using EasyOCR deep learning model."""
        reader = self._get_easyocr_reader()
        results = reader.readtext(image_path)

        lines = []
        total_confidence = 0.0
        for (bbox, text, confidence) in results:
            cleaned = text.strip()
            if cleaned:
                lines.append(cleaned)
                total_confidence += confidence

        avg_confidence = total_confidence / len(lines) if lines else 0.0
        raw_text = "\n".join(lines)

        return OCRResult(
            raw_text=raw_text,
            confidence=avg_confidence,
            lines=lines,
            source_engine="easyocr"
        )

    def _parse_with_tesseract(self, image_path: str) -> OCRResult:
        """Fallback parser using pytesseract."""
        image = Image.open(image_path)
        # Get detailed data for confidence
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        lines = []
        confidences = []
        current_line = []
        current_line_num = -1

        for i, text in enumerate(data["text"]):
            line_num = data["line_num"][i]
            conf = int(data["conf"][i])

            if line_num != current_line_num:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = []
                current_line_num = line_num

            if text.strip() and conf > 0:
                current_line.append(text.strip())
                confidences.append(conf / 100.0)

        if current_line:
            lines.append(" ".join(current_line))

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        raw_text = "\n".join(lines)

        return OCRResult(
            raw_text=raw_text,
            confidence=avg_confidence,
            lines=lines,
            source_engine="pytesseract"
        )

    def post_process(self, ocr_result: OCRResult) -> list[str]:
        """Clean and normalize OCR output lines."""
        processed = []
        for line in ocr_result.lines:
            # Remove excessive whitespace
            cleaned = " ".join(line.split())
            # Skip very short noise lines
            if len(cleaned) > 2:
                processed.append(cleaned)
        return processed
