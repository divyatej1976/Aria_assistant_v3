import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.core.errors import ValidationError
from app.services.ocr import (
    detect_image_mime,
    extract_text_from_image,
    extract_text_from_pdf,
)


def _create_sample_image(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=120)
    page.insert_text((30, 60), text, fontsize=18)
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes("png")


def _create_scanned_pdf(text: str) -> bytes:
    img_bytes = _create_sample_image(text)
    img_doc = pymupdf.open(stream=img_bytes, filetype="png")
    pdf_bytes = img_doc.convert_to_pdf()
    return pdf_bytes


def test_detect_image_mime_types():
    assert detect_image_mime(b"\x89PNG\r\n\x1a\n123456") == "image/png"
    assert detect_image_mime(b"\xff\xd8\xff\xe0" + b"\x00" * 20) == "image/jpeg"
    assert detect_image_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"

    with pytest.raises(ValidationError, match="Unsupported file format"):
        detect_image_mime(b"GIF89a...")

    with pytest.raises(ValidationError, match="exceeds the 25 MB limit"):
        detect_image_mime(b"\x89PNG\r\n\x1a\n" + b"0" * (26 * 1024 * 1024))


def test_ocr_extracts_text_from_rendered_image():
    img_bytes = _create_sample_image("Calculus Derivatives and Integrals 101")
    text = extract_text_from_image(img_bytes, mime_type="image/png")
    assert "Calculus" in text
    assert "Derivatives" in text


def test_ocr_extracts_text_from_scanned_pdf():
    pdf_bytes = _create_scanned_pdf("Microservices Architecture Patterns")
    text = extract_text_from_pdf(pdf_bytes)
    assert "Microservices" in text
    assert "Architecture" in text


def test_api_upload_image_resource(client: TestClient):
    # Register user and context
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"ocr-learner-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "name": "OCR Learner",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ctx = client.post(
        "/api/v1/contexts",
        headers=headers,
        json={"title": "Computer Networks", "description": "OSI model"},
    ).json()

    img_bytes = _create_sample_image("Transport Layer TCP vs UDP Protocol")

    # Upload image
    res = client.post(
        f"/api/v1/resources/image?context_id={ctx['id']}&title=TCP_UDP_Diagram",
        headers={**headers, "Content-Type": "image/png"},
        content=img_bytes,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["resource_type"] == "IMAGE"
    assert body["processing_status"] == "READY"
    assert body["chunk_count"] >= 1

    # Verify chunks contain the extracted text
    chunks_res = client.get(f"/api/v1/resources/{body['id']}/chunks", headers=headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 1
    assert "Transport Layer" in chunks[0]["content"] or "TCP" in chunks[0]["content"]
