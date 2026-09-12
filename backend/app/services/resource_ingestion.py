import re
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.registry import get_embedding_provider
from app.core.errors import ValidationError
from app.db.models import ConceptChunk, Resource, ResourceChunk
from app.services.audio import delete_artifacts_for_source as delete_audio_artifacts


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
    import fitz

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The uploaded PDF could not be read") from exc
    return "\n".join(page.get_text() for page in document)


async def _process_resource(db: Session, resource: Resource, text: str) -> Resource:
    try:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No readable text could be extracted")
        embeddings = await get_embedding_provider().embed(chunks)
        from app.core.config import get_settings

        expected_dim = get_settings().aria_embedding_dim
        for emb in embeddings:
            if len(emb) != expected_dim:
                raise ValueError(f"Embedding dimension {len(emb)} != expected {expected_dim}")
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            db.add(
                ResourceChunk(
                    owner_id=resource.owner_id,
                    resource_id=resource.id,
                    content=chunk,
                    chunk_index=index,
                    embedding_json=embedding,
                    embedding=embedding,
                    metadata_json={"source": resource.title},
                )
            )
        resource.processing_status = "READY"
        resource.error_detail = None
    except Exception as exc:
        resource.processing_status = "FAILED"
        resource.error_detail = str(exc)[:500]
    db.commit()
    db.refresh(resource)
    return resource


async def create_text_resource(
    db: Session, *, owner_id: UUID, context_id: UUID, title: str, text: str
) -> Resource:
    if not text.strip():
        raise ValidationError("Resource text cannot be empty")
    resource = Resource(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        resource_type="TEXT",
        processing_status="PROCESSING",
        source_text=text,
    )
    db.add(resource)
    db.flush()
    return await _process_resource(db, resource, text)


async def create_pdf_resource(
    db: Session, *, owner_id: UUID, context_id: UUID, title: str, content: bytes
) -> Resource:
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
        raw_bytes=content,
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
        text = extract_pdf_text(content)
    except ValueError as exc:
        resource.processing_status = "FAILED"
        resource.error_detail = str(exc)
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
    _delete_chunks_with_concept_links(db, resource=resource)
    delete_audio_artifacts(
        db, owner_id=resource.owner_id, source_type="RESOURCE", source_id=resource.id
    )
    db.delete(resource)
    db.commit()


async def reprocess_resource(db: Session, *, resource: Resource) -> Resource:
    _delete_chunks_with_concept_links(db, resource=resource)
    resource.processing_status = "PROCESSING"
    resource.error_detail = None
    db.commit()
    db.refresh(resource)
    if resource.resource_type == "TEXT":
        text = resource.source_text or ""
        return await _process_resource(db, resource, text)
    if resource.resource_type == "PDF":
        content = resource.raw_bytes or b""
        if not content.startswith(b"%PDF"):
            resource.processing_status = "UNSUPPORTED"
            resource.error_detail = "Unsupported file type; upload a PDF"
            db.commit()
            db.refresh(resource)
            return resource
        try:
            text = extract_pdf_text(content)
        except ValueError as exc:
            resource.processing_status = "FAILED"
            resource.error_detail = str(exc)
            db.commit()
            db.refresh(resource)
            return resource
        return await _process_resource(db, resource, text)
    resource.processing_status = "FAILED"
    resource.error_detail = "Unsupported resource type"
    db.commit()
    db.refresh(resource)
    return resource


async def replace_text_resource(
    db: Session, *, resource: Resource, title: str, text: str
) -> Resource:
    if resource.resource_type != "TEXT":
        raise ValidationError("A non-text resource cannot be replaced with pasted text")
    if not text.strip():
        raise ValidationError("Resource text cannot be empty")
    resource.title = title
    resource.source_text = text
    db.add(resource)
    db.commit()
    return await reprocess_resource(db, resource=resource)


async def replace_pdf_resource(
    db: Session, *, resource: Resource, title: str, content: bytes
) -> Resource:
    if resource.resource_type != "PDF":
        raise ValidationError("A non-PDF resource cannot be replaced with a PDF")
    resource.title = title
    resource.raw_bytes = content
    db.add(resource)
    db.commit()
    return await reprocess_resource(db, resource=resource)
