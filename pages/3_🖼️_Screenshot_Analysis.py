"""Screenshot Analysis Page for NextGen NewsVerify.

Safely accepts uploaded images or screenshots containing news stories,
applies OCR extraction, and allows user text correction before pipeline execution.
"""

from __future__ import annotations

import streamlit as st
from PIL import Image
import io

from services.ocr_service import OCRService
from security.input_validator import validate_image_file

st.set_page_config(page_title="Screenshot Analysis — NewsVerify", page_icon="🖼️", layout="wide")

st.title("🖼️ Screenshot & Image News Analysis")
st.markdown(
    "Upload a screenshot or photo of a news headline, social media post, or article snippet. "
    "The system extracts and isolates text via OCR and provides an editable preview for correction before analysis."
)

ocr_service = OCRService()

# Engine status indicator
col_status, col_guidance = st.columns([1, 2])
with col_status:
    if ocr_service.is_engine_available:
        st.success("OCR Engine: **Tesseract Functional**")
    else:
        st.info("OCR Engine: **Tesseract Not Detected** (Manual Transcript Mode Active)")

with col_guidance:
    if not ocr_service.is_engine_available:
        st.caption(
            "To enable automated image text extraction on Windows, install [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) "
            "or set the `TESSERACT_CMD` environment variable. You can still paste or transcribe text manually below."
        )

st.divider()

uploaded_file = st.file_uploader(
    "Upload News Screenshot (PNG, JPG, WEBP — Maximum 10MB):",
    type=["png", "jpg", "jpeg", "webp"],
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    # Validate image security
    is_valid, err_msg, detected_fmt = validate_image_file(file_bytes, filename)
    if not is_valid:
        st.error(f"Image rejected: {err_msg}")
    else:
        col_img, col_ocr = st.columns([1, 1])

        with col_img:
            st.subheader("Image Preview")
            try:
                pil_img = Image.open(io.BytesIO(file_bytes))
                st.image(pil_img, caption=f"{filename} ({detected_fmt}, {pil_img.size[0]}x{pil_img.size[1]}px)", use_container_width=True)
            except Exception as e:
                st.error(f"Could not render image preview: {e}")

        with col_ocr:
            st.subheader("Extracted Text & Verification")

            # Execute OCR if engine available
            extracted_text = ""
            if ocr_service.is_engine_available:
                with st.spinner("Extracting text with Tesseract OCR..."):
                    res = ocr_service.extract_text_from_image(file_bytes, filename)
                    if res["success"]:
                        extracted_text = res["text"]
                        st.success(f"Extracted {res['char_count']} characters.")
                    else:
                        st.error(res["error"])
            else:
                st.warning("Automated OCR extraction is unavailable. Please transcribe the visible text below:")

            # Editable Text Area for user correction
            corrected_text = st.text_area(
                "Review & Edit Extracted Text (Fix OCR errors, names, or numbers):",
                value=extracted_text,
                height=260,
                placeholder="Transcribe or correct text from the image here...",
            )

            if corrected_text and len(corrected_text.strip()) >= 30:
                if st.button("🚀 Transfer to News Analysis Pipeline", type="primary"):
                    st.session_state["ocr_transferred_text"] = corrected_text.strip()
                    st.success("Text transferred successfully! Navigate to 'Analyze News' to execute verification.")
            elif corrected_text:
                st.info("Please ensure text contains at least 30 characters before transferring to analysis.")
