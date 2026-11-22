"""Tests for input validation, sanitization, image verification, and secret masking."""

import io
from PIL import Image
from security.input_validator import (
    validate_text_input,
    validate_image_file,
    sanitize_html_content,
    sanitize_filename,
    mask_secret,
)


def test_validate_text_input_valid():
    """Verify standard length news text is accepted."""
    valid_text = "The Federal Reserve raised interest rates by 25 basis points at its meeting today."
    is_valid, err, cleaned = validate_text_input(valid_text)
    assert is_valid is True
    assert err == ""
    assert "Federal Reserve" in cleaned


def test_validate_text_input_short_and_empty():
    """Verify empty or overly short text is rejected."""
    is_valid, err, _ = validate_text_input("")
    assert is_valid is False
    assert "empty" in err.lower()

    is_valid, err, _ = validate_text_input("Too short.")
    assert is_valid is False
    assert "too short" in err.lower()


def test_validate_text_input_exceeds_max():
    """Verify huge input exceeding max limits is caught."""
    huge_text = "A" * 105_000
    is_valid, err, _ = validate_text_input(huge_text, max_chars=100_000)
    assert is_valid is False
    assert "exceeds maximum" in err.lower()


def test_sanitize_html_content_strips_scripts_and_events():
    """Verify script tags, iframes, and inline event handlers are removed."""
    malicious_html = """
    <div>
        <p>Legitimate news story paragraph.</p>
        <script>alert('xss')</script>
        <iframe src="http://evil.com"></iframe>
        <a href="javascript:stealCookies()" onclick="steal()">Click here</a>
    </div>
    """
    clean_html = sanitize_html_content(malicious_html)
    assert "<script>" not in clean_html
    assert "<iframe>" not in clean_html
    assert "javascript:" not in clean_html
    assert "onclick" not in clean_html
    assert "Legitimate news story" in clean_html


def test_validate_image_file_valid_png():
    """Verify valid PNG image bytes are accepted."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    is_valid, err, detected_fmt = validate_image_file(png_bytes, "screenshot.png")
    assert is_valid is True
    assert err == ""
    assert detected_fmt == "PNG"


def test_validate_image_file_invalid_extension():
    """Verify unauthorized file extensions are rejected."""
    is_valid, err, fmt = validate_image_file(b"dummy bytes", "malware.exe")
    assert is_valid is False
    assert "unsupported file extension" in err.lower()


def test_validate_image_file_corrupted_data():
    """Verify corrupted image bytes with image extension fail verification."""
    is_valid, err, fmt = validate_image_file(b"not an image", "test.png")
    assert is_valid is False
    assert "corrupted" in err.lower() or "invalid" in err.lower()


def test_sanitize_filename_traversal_prevention():
    """Verify path traversal characters are neutralized."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32.dll") == "system32.dll"
    assert ".." not in sanitize_filename("foo/../bar.png")


def test_mask_secret():
    """Verify API keys are masked for logs and UI display."""
    assert mask_secret("AIzaSyB1234567890abcdef") == "AIza...cdef"
    assert mask_secret("") == "<Not Configured>"
    assert mask_secret(None) == "<Not Configured>"
    assert mask_secret("short") == "****"
