import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import anyio.to_thread
from sqlalchemy import String, cast, delete, select, update
from sqlalchemy.orm import Session

from app.ai.registry import get_embedding_provider
from app.core.errors import ValidationError
from app.db.models import ConceptChunk, Resource, ResourceChunk
from app.services.audio import delete_artifacts_for_source as delete_audio_artifacts
from app.services.audio_storage import get_file_storage, remove_files
from app.services.contexts import get_owned_context
from app.services.ocr import (
    MAX_IMAGE_BYTES,
    detect_image_mime,
    extract_text_from_image,
    extract_text_from_pdf,
)

logger = logging.getLogger(__name__)


def _extraction_error(exc: Exception) -> str:
    known = {
        "The uploaded PDF could not be read",
        "The uploaded PDF could not be read or contains no readable text",
        "Failed to perform OCR on the uploaded image",
        "No readable text could be recognized from the image",
        "Unsupported file format. Please upload a PNG, JPEG, or WEBP image, or a PDF.",
        f"Image upload exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit",
    }
    message = str(exc)
    return message if message in known else "The uploaded file could not be processed. Please retry."


async def _extract_off_loop(extract: Callable[..., str], *args) -> str:
    """Run sync PyMuPDF/Tesseract extraction in a worker thread.

    These calls take seconds (OCR) and must never run on the event loop,
    where they would stall every concurrent request. Only pure
    bytes-in/str-out work crosses the thread boundary — the DB session stays
    on the loop thread.
    """
    return await anyio.to_thread.run_sync(extract, *args)


def _delete_chunks_with_concept_links(db: Session, *, resource: Resource) -> None:
    """Delete a resource's chunks FK-safely: concept links before chunks."""
    chunk_ids = select(ResourceChunk.id).where(ResourceChunk.resource_id == resource.id)
    db.execute(delete(ConceptChunk).where(ConceptChunk.chunk_id.in_(chunk_ids)))
    db.execute(delete(ResourceChunk).where(ResourceChunk.resource_id == resource.id))
    db.flush()


def chunk_text(text: str, *, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if overlap >= size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks


def extract_pdf_text(content: bytes) -> str:
    return extract_text_from_pdf(content)


def _resource_version(db: Session, resource: Resource) -> str:
    # SQLite server-default timestamps omit fractional seconds. Compare their
    # original stored representation rather than binding a reformatted datetime.
    version = db.scalar(select(cast(Resource.updated_at, String)).where(
        Resource.id == resource.id, Resource.owner_id == resource.owner_id,
    ))
    if version is None or datetime.fromisoformat(version) != resource.updated_at:
        raise ValidationError("Resource changed during processing. Reload and try again.")
    return version


def _record_processing_failure(
    db: Session, resource: Resource, message: str, *, expected_version: str | None = None,
) -> Resource:
    version = expected_version if expected_version is not None else _resource_version(db, resource)
    previous_ready = resource.processing_status == "READY"
    db.execute(update(Resource).where(
        Resource.id == resource.id, Resource.owner_id == resource.owner_id,
        cast(Resource.updated_at, String) == version,
    ).values(
        processing_status="READY" if previous_ready else "FAILED",
        error_detail=("Reprocessing failed. Your previous material remains available." if previous_ready else message),
        updated_at=datetime.now(UTC),
    ), execution_options={"synchronize_session": False})
    db.commit()
    db.refresh(resource)
    return resource


async def _process_resource(
    db: Session, resource: Resource, text: str, *, replace_existing: bool = False,
    replacements: dict | None = None, expected_version: str | None = None,
) -> Resource:
    expected_version = expected_version if expected_version is not None else _resource_version(db, resource)
    try:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No readable text could be extracted")
        from app.ai.providers import DeterministicEmbeddingProvider
        from app.core.config import get_settings

        provider = get_embedding_provider()
        # Hashed stand-in vectors are never used for search (study.semantic_scoring_available), so
        # without a real embedding key nothing is stored: ~10 KB saved per chunk.
        semantic = not isinstance(provider, DeterministicEmbeddingProvider)
        embeddings = await provider.embed(chunks) if semantic else [None] * len(chunks)
        # Postgres keeps the native vector only; the JSON copy is for SQLite, which has no vector type.
        keep_json = db.get_bind().dialect.name != "postgresql"
        expected_dim = get_settings().aria_embedding_dim
        # Fully validate and stage the new version before deleting usable data.
        staged = []
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            if embedding is not None and len(embedding) != expected_dim:
                raise ValueError("Unexpected embedding dimensions")
            staged.append(ResourceChunk(
                owner_id=resource.owner_id, resource_id=resource.id, content=chunk, chunk_index=index,
                embedding_json=embedding if keep_json else None, embedding=embedding,
                metadata_json={"source": (replacements or {}).get("title", resource.title)},
            ))
    except Exception:
        return _record_processing_failure(
            db, resource, "Resource processing failed. Please retry.", expected_version=expected_version
        )

    try:
        with db.begin_nested():
            claimed = db.execute(update(Resource).where(
                Resource.id == resource.id, Resource.owner_id == resource.owner_id,
                cast(Resource.updated_at, String) == expected_version,
            ).values(
                **(replacements or {}), source_text=text, processing_status="READY", error_detail=None,
                updated_at=datetime.now(UTC),
            ), execution_options={"synchronize_session": False}).rowcount
            if not claimed:
                raise ValidationError("Resource changed during processing. Reload and try again.")
            if replace_existing:
                _delete_chunks_with_concept_links(db, resource=resource)
            db.add_all(staged)
            db.flush()
        db.commit()
        db.refresh(resource)
        return resource
    except ValidationError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        db.refresh(resource)
        return _record_processing_failure(
            db, resource, "Resource processing failed. Please retry.", expected_version=expected_version
        )


async def create_text_resource(
    db: Session, *, owner_id: UUID, context_id: UUID, title: str, text: str,
    resource_id: UUID | None = None, study_session_id: UUID | None = None,
) -> Resource:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    if resource_id is not None:
        existing = db.get(Resource, resource_id)
        if existing is not None:
            if existing.owner_id != owner_id or existing.context_id != context_id:
                raise ValidationError("Resource not found")
            return existing
    if not text.strip():
        raise ValidationError("Resource text cannot be empty")
    _check_file_limit(db, owner_id)
    resource = Resource(
        **({"id": resource_id} if resource_id is not None else {}),
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        resource_type="TEXT",
        processing_status="PROCESSING",
        source_text=text,
        study_session_id=study_session_id,
    )
    db.add(resource)
    # Keep the original source durable before processing, as for PDF/image
    # uploads. A chunk-write rollback must not remove the resource itself.
    db.commit()
    db.refresh(resource)
    return await _process_resource(db, resource, text)


def _check_file_limit(db: Session, owner_id: UUID) -> None:
    """One account cannot fill the shared storage: a cap on saved files (library and chat)."""
    from sqlalchemy import func

    from app.core.config import get_settings

    limit = get_settings().aria_max_files_per_user
    if limit and (db.scalar(select(func.count(Resource.id)).where(Resource.owner_id == owner_id)) or 0) >= limit:
        raise ValidationError(f"You have {limit} saved files, the most an account can keep. "
                              "Delete some in the Library to add more.")


def _store_original(owner_id: UUID, content: bytes, content_type: str | None) -> dict:
    """Keep an uploaded original in file storage (Blob), not the database: databases are
    small and priced by size. If storage is unavailable, the bytes stay in the row."""
    resource_id = uuid4()
    try:
        key = get_file_storage().save(owner_id=owner_id, artifact_id=resource_id,
                                      content_type=content_type, data=content)
        return {"id": resource_id, "storage_key": key, "raw_bytes": None}
    except Exception:
        logger.exception("file storage failed; keeping the original in the database")
        return {"id": resource_id, "raw_bytes": content}


def original_bytes(resource: Resource) -> bytes | None:
    """An upload's original file, wherever it is kept."""
    if resource.raw_bytes is not None:
        return resource.raw_bytes
    return get_file_storage().load(resource.storage_key) if resource.storage_key else None


async def create_pdf_resource(
    db: Session, *, owner_id: UUID, context_id: UUID, title: str, content: bytes,
    study_session_id: UUID | None = None,
) -> Resource:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    _check_file_limit(db, owner_id)
    try:
        import fitz  # noqa: F401
    except ImportError as exc:
        raise ValidationError(
            "PDF support is not installed. Install the pymupdf dependency."
        ) from exc
    resource = Resource(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        resource_type="PDF",
        processing_status="PROCESSING",
        study_session_id=study_session_id,
        **_store_original(owner_id, content, "application/pdf"),
    )
    db.add(resource)
    db.flush()
    if not content.startswith(b"%PDF"):
        resource.processing_status = "UNSUPPORTED"
        resource.error_detail = "Unsupported file type; upload a PDF"
        db.commit()
        db.refresh(resource)
        return resource
    try:
        text = await _extract_off_loop(extract_pdf_text, content)
    except ValueError as exc:
        resource.processing_status = "FAILED"
        resource.error_detail = _extraction_error(exc)
        db.commit()
        db.refresh(resource)
        return resource
    resource.source_text = text
    db.commit()
    db.refresh(resource)
    return await _process_resource(db, resource, text)


async def create_image_resource(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    title: str,
    content: bytes,
    mime_type: str | None = None,
    study_session_id: UUID | None = None,
) -> Resource:
    """Ingest an image study resource using OCR text extraction."""
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    _check_file_limit(db, owner_id)
    try:
        mime = detect_image_mime(content) if not mime_type else mime_type
    except ValidationError as exc:
        resource = Resource(
            owner_id=owner_id,
            context_id=context_id,
            title=title,
            resource_type="IMAGE",
            processing_status="UNSUPPORTED",
            error_detail=_extraction_error(exc),
            study_session_id=study_session_id,
            **_store_original(owner_id, content, None),
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    resource = Resource(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        resource_type="IMAGE",
        processing_status="PROCESSING",
        study_session_id=study_session_id,
        **_store_original(owner_id, content, mime),
    )
    db.add(resource)
    db.flush()

    try:
        text = await _extract_off_loop(extract_text_from_image, content, mime)
        resource.source_text = text
        db.commit()
        db.refresh(resource)
    except ValueError as exc:
        resource.processing_status = "FAILED"
        resource.error_detail = _extraction_error(exc)
        db.commit()
        db.refresh(resource)
        return resource

    return await _process_resource(db, resource, text)


def get_owned_resource(
    db: Session, *, owner_id: UUID, resource_id: UUID
) -> Resource | None:
    return db.scalar(
        select(Resource).where(Resource.id == resource_id, Resource.owner_id == owner_id)
    )


def delete_resource(db: Session, *, resource: Resource) -> None:
    stored = resource.storage_key
    _delete_chunks_with_concept_links(db, resource=resource)
    delete_audio_artifacts(
        db, owner_id=resource.owner_id, source_type="RESOURCE", source_id=resource.id
    )
    db.delete(resource)
    db.commit()
    remove_files([stored])


async def reprocess_resource(
    db: Session, *, resource: Resource, replacements: dict | None = None,
) -> Resource:
    changes = replacements or {}
    expected_version = _resource_version(db, resource)
    if resource.resource_type == "TEXT":
        text = changes.get("source_text", resource.source_text) or ""
        # source_text is set exactly once with the staged chunks.
        changes = {key: value for key, value in changes.items() if key != "source_text"}
    elif resource.resource_type in ("PDF", "IMAGE"):
        content = changes.get("raw_bytes") or original_bytes(resource) or b""
        if resource.resource_type == "PDF" and not content.startswith(b"%PDF"):
            return _record_processing_failure(
                db, resource, "Unsupported file type; upload a PDF", expected_version=expected_version
            )
        try:
            extractor = extract_pdf_text if resource.resource_type == "PDF" else extract_text_from_image
            text = await _extract_off_loop(extractor, content)
        except (ValueError, ValidationError):
            return _record_processing_failure(
                db, resource, "The uploaded file could not be read", expected_version=expected_version
            )
    else:
        return _record_processing_failure(
            db, resource, "Unsupported resource type", expected_version=expected_version
        )
    return await _process_resource(
        db, resource, text, replace_existing=True, replacements=changes, expected_version=expected_version
    )


async def replace_text_resource(
    db: Session, *, resource: Resource, title: str, text: str
) -> Resource:
    if resource.resource_type != "TEXT":
        raise ValidationError("A non-text resource cannot be replaced with pasted text")
    if not text.strip():
        raise ValidationError("Resource text cannot be empty")
    return await reprocess_resource(db, resource=resource, replacements={"title": title, "source_text": text})


async def replace_pdf_resource(
    db: Session, *, resource: Resource, title: str, content: bytes
) -> Resource:
    if resource.resource_type != "PDF":
        raise ValidationError("A non-PDF resource cannot be replaced with a PDF")
    return await reprocess_resource(db, resource=resource, replacements={"title": title, "raw_bytes": content})
