from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import LearningContext, Resource, ResourceChunk, StudySession, UploadChunk
from app.schemas.resources import (
    ChunkResponse,
    ResourceResponse,
    TextResourceCreate,
    TextResourceUpdate,
)
from app.security.dependencies import CurrentLearner
from app.services.digest import schedule_digest
from app.services.resource_ingestion import (
    create_image_resource,
    create_pdf_resource,
    create_text_resource,
    delete_resource,
    get_owned_resource,
    replace_pdf_resource,
    replace_text_resource,
    reprocess_resource,
)

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])
Db = Annotated[Session, Depends(get_db)]

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB: textbooks and lecture packs fit
# Some hosts cap a request body (Vercel: 4.5 MB), so bigger files arrive in pieces of at most this.
MAX_PIECE_BYTES = 4 * 1024 * 1024


@router.put("/uploads/{upload_id}/{seq}", status_code=204)
async def add_upload_piece(upload_id: UUID, seq: int, learner: CurrentLearner, db: Db, request: Request) -> None:
    """Store one piece of a large file; the upload endpoint then takes `upload_id` instead of a body."""
    if not 0 <= seq < MAX_UPLOAD_BYTES // MAX_PIECE_BYTES + 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload piece")
    data = await request.body()
    if not data or len(data) > MAX_PIECE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each upload piece must be 1 byte to 4 MB")
    db.execute(delete(UploadChunk).where(UploadChunk.owner_id == learner.id, UploadChunk.upload_id == upload_id,
                                         UploadChunk.seq == seq))  # a retried piece replaces the first try
    db.add(UploadChunk(owner_id=learner.id, upload_id=upload_id, seq=seq, data=data))
    db.commit()


async def read_upload_body(request: Request, db: Session | None = None, owner_id: UUID | None = None) -> bytes:
    """Read the upload, enforcing the size cap: the request body, or the pieces sent for `upload_id`."""
    upload_id = request.query_params.get("upload_id")
    if upload_id and db is not None and owner_id is not None:
        try:
            upload = UUID(upload_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload id") from exc
        pieces = db.scalars(select(UploadChunk.data).where(
            UploadChunk.owner_id == owner_id, UploadChunk.upload_id == upload).order_by(UploadChunk.seq)).all()
        content = b"".join(pieces)
        db.execute(delete(UploadChunk).where(UploadChunk.owner_id == owner_id, UploadChunk.upload_id == upload))
        db.commit()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                                detail=f"This file is over {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. "
                                       "Try a smaller file or split it.")
        return content
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"This file is over {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Try a smaller file or split it.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def ensure_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning context not found"
        )
    return context


def ensure_chat(db: Session, *, session_id: UUID | None, context_id: UUID, owner_id: UUID) -> UUID | None:
    """A chat attachment must belong to one of the learner's chats in this subject."""
    if session_id is None:
        return None
    chat = db.scalar(select(StudySession).where(
        StudySession.id == session_id, StudySession.owner_id == owner_id,
        StudySession.context_id == context_id,
    ))
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat.id


def get_resource(db: Session, *, resource_id: UUID, owner_id: UUID) -> Resource:
    resource = get_owned_resource(db, owner_id=owner_id, resource_id=resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


def resource_response(resource: Resource, *, chunk_count: int = 0) -> ResourceResponse:
    return ResourceResponse(
        id=str(resource.id),
        context_id=str(resource.context_id),
        title=resource.title,
        resource_type=resource.resource_type,
        processing_status=resource.processing_status,
        error_detail=resource.error_detail,
        chunk_count=chunk_count,
        created_at=resource.created_at,
        session_id=str(resource.study_session_id) if resource.study_session_id else None,
    )


def chunk_count_for(db: Session, *, resource_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count(ResourceChunk.id)).where(ResourceChunk.resource_id == resource_id)
        )
        or 0
    )


@router.post("/text", response_model=ResourceResponse, status_code=201)
async def add_text_resource(
    request: TextResourceCreate, learner: CurrentLearner, db: Db
) -> ResourceResponse:
    ensure_context(db, context_id=request.context_id, owner_id=learner.id)
    resource = await create_text_resource(
        db, owner_id=learner.id, context_id=request.context_id, title=request.title, text=request.text
    )
    schedule_digest(db, owner_id=learner.id, resource_id=resource.id)
    return resource_response(resource, chunk_count=chunk_count_for(db, resource_id=resource.id))


@router.post("/pdf", response_model=ResourceResponse, status_code=201)
async def add_pdf_resource(
    learner: CurrentLearner,
    db: Db,
    request: Request,
    context_id: UUID,
    title: str = "Uploaded PDF",
    session_id: UUID | None = None,
) -> ResourceResponse:
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    chat_id = ensure_chat(db, session_id=session_id, context_id=context_id, owner_id=learner.id)
    content = await read_upload_body(request, db, learner.id)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty PDF upload")
    resource = await create_pdf_resource(
        db,
        owner_id=learner.id,
        context_id=context_id,
        title=title,
        content=content,
        study_session_id=chat_id,
    )
    schedule_digest(db, owner_id=learner.id, resource_id=resource.id)
    return resource_response(resource, chunk_count=chunk_count_for(db, resource_id=resource.id))


@router.post("/image", response_model=ResourceResponse, status_code=201)
async def add_image_resource(
    learner: CurrentLearner,
    db: Db,
    request: Request,
    context_id: UUID,
    title: str = "Uploaded Image",
    session_id: UUID | None = None,
) -> ResourceResponse:
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    chat_id = ensure_chat(db, session_id=session_id, context_id=context_id, owner_id=learner.id)
    content = await read_upload_body(request, db, learner.id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image content cannot be empty",
        )
    content_type = request.headers.get("content-type")
    resource = await create_image_resource(
        db,
        owner_id=learner.id,
        context_id=context_id,
        title=title,
        content=content,
        mime_type=content_type,
        study_session_id=chat_id,
    )
    schedule_digest(db, owner_id=learner.id, resource_id=resource.id)
    return resource_response(resource, chunk_count=chunk_count_for(db, resource_id=resource.id))


@router.get("", response_model=list[ResourceResponse])
def list_resources(
    learner: CurrentLearner, db: Db, context_id: UUID, session_id: UUID | None = None,
) -> list[ResourceResponse]:
    """The subject's shared library, or with session_id the files attached in that chat."""
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    resources = db.scalars(
        select(Resource)
        .where(
            Resource.owner_id == learner.id, Resource.context_id == context_id,
            Resource.study_session_id == session_id if session_id else Resource.study_session_id.is_(None),
        )
        .order_by(Resource.created_at)
        .limit(100)
    ).all()
    # One GROUP BY instead of one COUNT per resource (N+1).
    counts = dict(
        db.execute(
            select(ResourceChunk.resource_id, func.count(ResourceChunk.id))
            .where(ResourceChunk.resource_id.in_([item.id for item in resources]))
            .group_by(ResourceChunk.resource_id)
        ).all()
    )
    return [
        resource_response(resource, chunk_count=counts.get(resource.id, 0))
        for resource in resources
    ]


@router.post("/{resource_id}/library", response_model=ResourceResponse)
def add_to_library(resource_id: UUID, learner: CurrentLearner, db: Db) -> ResourceResponse:
    """Share a file attached in one chat with every chat in the subject."""
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    if resource.study_session_id is not None:
        resource.study_session_id = None
        db.commit()
        db.refresh(resource)
    return resource_response(resource, chunk_count=chunk_count_for(db, resource_id=resource.id))


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource_detail(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    return resource_response(resource, chunk_count=chunk_count_for(db, resource_id=resource.id))


@router.get("/{resource_id}/chunks", response_model=list[ChunkResponse])
def list_resource_chunks(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> list[ChunkResponse]:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    if resource.processing_status != "READY":
        return []
    chunks = db.scalars(
        select(ResourceChunk)
        .where(ResourceChunk.resource_id == resource.id)
        .order_by(ResourceChunk.chunk_index)
        .limit(3)
    ).all()
    return [
        ChunkResponse(chunk_index=chunk.chunk_index, content=chunk.content)
        for chunk in chunks
    ]


@router.delete("/{resource_id}")
def delete_resource_route(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, str]:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    delete_resource(db, resource=resource)
    return {"detail": "Resource deleted"}


@router.post("/{resource_id}/process", response_model=ResourceResponse)
async def retry_processing(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    processed = await reprocess_resource(db, resource=resource)
    processed.digest = None  # the file changed; condense it again
    db.commit()
    schedule_digest(db, owner_id=learner.id, resource_id=processed.id)
    return resource_response(processed, chunk_count=chunk_count_for(db, resource_id=processed.id))


@router.put("/{resource_id}/text", response_model=ResourceResponse)
async def replace_text(
    resource_id: UUID,
    request: TextResourceUpdate,
    learner: CurrentLearner,
    db: Db,
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    replaced = await replace_text_resource(
        db, resource=resource, title=request.title, text=request.text
    )
    replaced.digest = None  # the file changed; condense it again
    db.commit()
    schedule_digest(db, owner_id=learner.id, resource_id=replaced.id)
    return resource_response(replaced, chunk_count=chunk_count_for(db, resource_id=replaced.id))


@router.put("/{resource_id}/pdf", response_model=ResourceResponse)
async def replace_pdf(
    resource_id: UUID,
    learner: CurrentLearner,
    db: Db,
    request: Request,
    title: str = "Uploaded PDF",
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    content = await read_upload_body(request, db, learner.id)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty PDF upload")
    replaced = await replace_pdf_resource(
        db, resource=resource, title=title, content=content
    )
    replaced.digest = None  # the file changed; condense it again
    db.commit()
    schedule_digest(db, owner_id=learner.id, resource_id=replaced.id)
    return resource_response(replaced, chunk_count=chunk_count_for(db, resource_id=replaced.id))
