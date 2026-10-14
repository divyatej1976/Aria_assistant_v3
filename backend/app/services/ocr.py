import logging
import os
import shutil
import tempfile
from pathlib import Path

import pymupdf

from app.core.errors import ValidationError

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

_CACHED_TESSDATA_DIR: str | None = None


def ensure_tessdata_dir() -> str:
    """Resolve a safe ASCII path for Tesseract eng.traineddata.

    Tesseract C++ internals on Windows fail when opening paths containing
    non-ASCII characters. If the project directory path contains non-ASCII
    codepoints, we mirror eng.traineddata to the system temp directory.
    """
    global _CACHED_TESSDATA_DIR
    if _CACHED_TESSDATA_DIR and os.path.exists(os.path.join(_CACHED_TESSDATA_DIR, "eng.traineddata")):
        return _CACHED_TESSDATA_DIR

    pkg_dir = Path(__file__).resolve().parent.parent / "resources" / "tessdata"
    pkg_traineddata = pkg_dir / "eng.traineddata"

    # Test if pkg_dir path is pure ASCII and exists
    pkg_str = str(pkg_dir)
    is_ascii = all(ord(c) < 128 for c in pkg_str)

    if is_ascii and pkg_traineddata.is_file():
        _CACHED_TESSDATA_DIR = pkg_str
        return _CACHED_TESSDATA_DIR

    # Fallback to ASCII temp directory
    temp_dir = Path(tempfile.gettempdir()) / "aria_tessdata"
    temp_dir.mkdir(parents=True, exist_ok=True)
    target = temp_dir / "eng.traineddata"

    if pkg_traineddata.is_file() and (not target.is_file() or target.stat().st_size == 0):
        shutil.copy2(pkg_traineddata, target)

    _CACHED_TESSDATA_DIR = str(temp_dir)
    return _CACHED_TESSDATA_DIR


def detect_image_mime(content: bytes) -> str:
    """Detect supported image MIME type by inspecting magic headers."""
    if len(content) > MAX_IMAGE_BYTES:
        raise ValidationError(f"Image upload exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise ValidationError("Unsupported file format. Please upload a PNG, JPEG, or WEBP image, or a PDF.")


def extract_text_from_image(image_bytes: bytes, mime_type: str | None = None) -> str:
    """Extract text from an image using PyMuPDF native OCR."""
    if not mime_type:
        mime_type = detect_image_mime(image_bytes)

    # Determine file extension for PyMuPDF
    ext = "png"
    if "jpeg" in mime_type or "jpg" in mime_type:
        ext = "jpeg"
    elif "webp" in mime_type:
        ext = "webp"

    try:
        img_doc = pymupdf.open(stream=image_bytes, filetype=ext)
        pdf_bytes = img_doc.convert_to_pdf()
        pdf_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        page = pdf_doc[0]
        tess_dir = ensure_tessdata_dir()
        tp = page.get_textpage_ocr(tessdata=tess_dir, dpi=150)
        extracted = tp.extractText().strip()
    except Exception as exc:
        logger.exception("OCR extraction failed")
        raise ValueError("Failed to perform OCR on the uploaded image") from exc

    if not extracted:
        raise ValueError("No readable text could be recognized from the image")
    return extracted


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF with automatic OCR fallback for scanned pages."""
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The uploaded PDF could not be read") from exc

    pages_text: list[str] = []
    tess_dir: str | None = None

    for i, page in enumerate(doc):
        # First attempt fast digital text extraction
        text = page.get_text().strip()
        # If the page has little or no text (e.g. scanned page or slide picture), run OCR
        if len(text) < 25:
            try:
                if tess_dir is None:
                    tess_dir = ensure_tessdata_dir()
                tp = page.get_textpage_ocr(tessdata=tess_dir, dpi=150)
                ocr_text = tp.extractText().strip()
                if ocr_text:
                    text = ocr_text
            except Exception:
                logger.warning("OCR failed on PDF page %d; keeping native text if any", i, exc_info=True)
        if text:
            pages_text.append(text)

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        raise ValueError("The uploaded PDF could not be read or contains no readable text")
    return full_text
