"""OCR Service for NextGen NewsVerify.

Safely decodes image bytes, locates or executes Tesseract OCR via pytesseract,
and extracts editable text from screenshots or news photos.
"""

from __future__ import annotations

import io
import os
import shutil
from typing import Dict, Any, Optional
from PIL import Image

from security.input_validator import validate_image_file


class OCRService:
    """Safe optical character recognition engine with automatic tesseract discovery."""

    COMMON_TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"/usr/bin/tesseract",
        r"/usr/local/bin/tesseract",
    ]

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd or os.getenv("TESSERACT_CMD")
        self._configure_pytesseract()

    def _configure_pytesseract(self) -> None:
        """Find and configure tesseract executable if available."""
        try:
            import pytesseract

            # If user specified or environment variable set
            if self.tesseract_cmd and os.path.exists(self.tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                return

            # Check if tesseract is on PATH
            if shutil.which("tesseract"):
                return

            # Check common installation locations
            for path in self.COMMON_TESSERACT_PATHS:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    self.tesseract_cmd = path
                    return
        except ImportError:
            pass

    @property
    def is_engine_available(self) -> bool:
        """Check if pytesseract and Tesseract binary are both installed and functional."""
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            return bool(version)
        except Exception:
            return False

    def extract_text_from_image(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate, decode, and extract text from an image upload."""
        # 1. Security validation
        is_valid, err_msg, detected_fmt = validate_image_file(file_bytes, filename)
        if not is_valid:
            return {
                "success": False,
                "text": "",
                "error": err_msg,
                "engine_available": self.is_engine_available,
            }

        # 2. Check engine availability
        if not self.is_engine_available:
            return {
                "success": False,
                "text": "",
                "error": (
                    "Tesseract OCR engine is not installed or not found on system PATH. "
                    "Install Tesseract-OCR (https://github.com/tesseract-ocr/tesseract) or "
                    "provide the executable path via the TESSERACT_CMD environment variable."
                ),
                "engine_available": False,
                "image_format": detected_fmt,
                "file_size_bytes": len(file_bytes),
            }

        # 3. Safe image decoding and preprocessing
        try:
            import pytesseract
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Convert RGBA / Palette images to RGB
                rgb_img = img.convert("RGB")
                extracted_text = pytesseract.image_to_string(rgb_img, lang="eng")
                cleaned_text = extracted_text.strip()

                return {
                    "success": True,
                    "text": cleaned_text,
                    "image_format": detected_fmt,
                    "dimensions": img.size,
                    "engine_available": True,
                    "char_count": len(cleaned_text),
                }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "error": f"OCR processing failed: {str(e)}",
                "engine_available": True,
            }
