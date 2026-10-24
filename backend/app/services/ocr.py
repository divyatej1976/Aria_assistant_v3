import logging
import os
import shutil
import tempfile
from pathlib import Path

import pymupdf

from app.core.errors import ValidationError

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB: full-resolution phone photos
MAX_OCR_PAGES = 50

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


VISION_PROMPT = (
    "Transcribe all the text in this image exactly, including handwriting, keeping its order, "
    "numbering and line breaks. Write formulas in plain text. If there is a diagram or table, "
    "describe it briefly in brackets. Output only the transcription."
)


def extract_text_from_image(image_bytes: bytes, mime_type: str | None = None) -> str:
    """Read an image's text: Gemini vision when configured (it reads handwriting and photos of
    notes), else Tesseract OCR, which only manages clean printed text."""
    if not mime_type:
        mime_type = detect_image_mime(image_bytes)
    from app.core.config import get_settings

    settings = get_settings()
    readers = []
    if getattr(settings, "openai_api_key", None):
        readers.append(lambda: _openai_vision_text(image_bytes, mime_type, key=settings.openai_api_key,
                                                   model=settings.aria_openai_vision_model))
    if getattr(settings, "gemini_api_key", None):
        readers.append(lambda: _vision_text(image_bytes, mime_type, key=settings.gemini_api_key,
                                            model=settings.aria_vision_model))
    for read in readers:
        try:
            text = read()
            if text:
                return text
        except Exception as exc:  # noqa: BLE001 - try the next reader, then local OCR
            logger.warning("vision transcription failed, trying the next reader error_type=%s", type(exc).__name__)
    return _tesseract_text(image_bytes, mime_type)


def _openai_vision_text(image_bytes: bytes, mime_type: str, *, key: str, model: str) -> str:
    import base64

    import httpx

    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": [
            {"type": "text", "text": VISION_PROMPT},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}]},
        timeout=90,
    )
    response.raise_for_status()
    return (response.json()["choices"][0]["message"].get("content") or "").strip()


def _vision_text(image_bytes: bytes, mime_type: str, *, key: str, model: str) -> str:
    import base64

    import httpx

    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": [
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}},
                {"text": VISION_PROMPT},
            ]}],
            # No "thinking": a transcription needs none, and it would add most of a minute.
            "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingBudget": 0}},
        },
        timeout=90,
    )
    response.raise_for_status()
    parts = response.json()["candidates"][0]["content"].get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def _tesseract_text(image_bytes: bytes, mime_type: str) -> str:
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
    ocr_pages = 0
    skipped = 0

    for i, page in enumerate(doc):
        # First attempt fast digital text extraction
        text = page.get_text().strip()
        # If the page has little or no text (e.g. scanned page or slide picture), run OCR
        # shortcut: OCR is ~1-2 s a page, so only the first MAX_OCR_PAGES scanned pages
        # are read in the request; long scans need a background OCR job.
        if len(text) < 25 and ocr_pages >= MAX_OCR_PAGES:
            skipped += 1
        elif len(text) < 25:
            ocr_pages += 1
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
    if skipped:
        # Say so in the text itself, so the tutor never presents a partial scan as the whole file.
        full_text += (f"\n\n[Note: {skipped} more scanned page(s) were not read; only the first "
                      f"{MAX_OCR_PAGES} scanned pages are transcribed. Upload the rest as a separate file.]")
    return full_text
