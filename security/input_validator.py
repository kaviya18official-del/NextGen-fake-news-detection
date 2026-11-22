"""Input validation, sanitization, and security utilities for NextGen NewsVerify.

Enforces constraints on text length, file uploads, safe file naming,
HTML script stripping, and secret redacting.
"""

from __future__ import annotations

import io
import os
import re
from typing import Tuple, Optional
from PIL import Image
from bs4 import BeautifulSoup

# Allowed image MIME types and extensions
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

MIN_TEXT_CHARS = 30
MAX_TEXT_CHARS = 100_000


def validate_text_input(
    text: Optional[str],
    min_chars: int = MIN_TEXT_CHARS,
    max_chars: int = MAX_TEXT_CHARS,
) -> Tuple[bool, str, str]:
    """Validate article or claim text input.

    Returns:
        (is_valid, error_message, cleaned_text)
    """
    if text is None:
        return False, "Input text cannot be empty.", ""

    # Remove null bytes and carriage returns
    cleaned = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    stripped = cleaned.strip()

    if len(stripped) == 0:
        return False, "Input text cannot be empty.", ""

    if len(stripped) < min_chars:
        return False, f"Input text is too short ({len(stripped)} chars). Minimum required is {min_chars} characters.", ""

    if len(stripped) > max_chars:
        return False, f"Input text exceeds maximum allowed length of {max_chars:,} characters.", ""

    return True, "", stripped


def validate_image_file(
    file_bytes: bytes,
    filename: str,
    max_size: int = MAX_IMAGE_SIZE_BYTES,
) -> Tuple[bool, str, Optional[str]]:
    """Validate an uploaded image for file size, extension, and safe decoding.

    Returns:
        (is_valid, error_message, detected_format)
    """
    if not file_bytes:
        return False, "Uploaded image is empty.", None

    if len(file_bytes) > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"Image size exceeds maximum limit of {max_mb:.1f} MB.", None

    # Check extension
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return (
            False,
            f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
            None,
        )

    # Decode and verify image header safely using PIL
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img_format = img.format
            if not img_format or img_format.upper() not in ALLOWED_IMAGE_FORMATS:
                return (
                    False,
                    f"Unsupported image format '{img_format}'. Only PNG, JPEG, and WEBP are permitted.",
                    None,
                )
            # Verify integrity
            img.verify()
            return True, "", img_format.upper()
    except Exception as e:
        return False, f"Invalid or corrupted image data: {str(e)}", None


def sanitize_html_content(raw_html: str) -> str:
    """Sanitize extracted HTML to prevent XSS and malicious script execution.

    Strips script, style, iframe, object, embed, and dangerous attributes.
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove dangerous elements
    dangerous_tags = [
        "script", "style", "iframe", "object", "embed", "applet",
        "form", "input", "button", "link", "meta", "base"
    ]
    for tag in soup(dangerous_tags):
        tag.decompose()

    # Clean attributes on all remaining tags
    for tag in soup.find_all(True):
        tag_attrs = dict(tag.attrs)
        for attr, val in tag_attrs.items():
            attr_lower = attr.lower()
            val_str = str(val).lower() if val else ""

            # Remove inline event handlers (onclick, onload, onerror, etc.)
            if attr_lower.startswith("on"):
                del tag.attrs[attr]
            # Remove javascript: or vbscript: or data: in href/src
            elif attr_lower in ("href", "src", "action", "data") and (
                "javascript:" in val_str or "vbscript:" in val_str or "data:" in val_str
            ):
                del tag.attrs[attr]

    return str(soup)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and shell injection."""
    if not filename:
        return "unnamed_file"

    # Remove directory separators
    clean = os.path.basename(filename)
    # Strip illegal filesystem chars
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    # Prevent hidden files or double dots
    clean = clean.lstrip(".").replace("..", "_")
    return clean[:128] if clean else "unnamed_file"


def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """Mask a sensitive API key or secret for display or logging."""
    if not secret:
        return "<Not Configured>"

    secret_str = str(secret).strip()
    if len(secret_str) <= visible_chars * 2:
        return "****"

    prefix = secret_str[:visible_chars]
    suffix = secret_str[-visible_chars:]
    return f"{prefix}...{suffix}"
