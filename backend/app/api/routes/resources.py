from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import LearningContext, Resource, ResourceChunk
from app.schemas.resources import (
    ChunkResponse,
    ResourceResponse,
    TextResourceCreate,
    TextResourceUpdate,
)
from app.security.dependencies import CurrentLearner
from app.services.resource_ingestion import (
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

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB PDF cap


async def read_upload_body(request: Request) -> bytes:
    """Read the request body streaming, enforcing the upload size cap."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"PDF upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
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


def get_resource(db: Session, *, resource_id: UUID, owner_id: UUID) -> Resource:
    resource = get_owned_resource(db, owner_id=owner_id, resource_id=resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


def resource_response(db: Session, resource: Resource) -> ResourceResponse:
    count = db.scalar(
        select(func.count(ResourceChunk.id)).where(ResourceChunk.resource_id == resource.id)
    )
    return ResourceResponse(
        id=str(resource.id),
        context_id=str(resource.context_id),
        title=resource.title,
        resource_type=resource.resource_type,
        processing_status=resource.processing_status,
        error_detail=resource.error_detail,
        chunk_count=count or 0,
        created_at=resource.created_at,
    )


@router.post("/text", response_model=ResourceResponse, status_code=201)
async def add_text_resource(
    request: TextResourceCreate, learner: CurrentLearner, db: Db
) -> ResourceResponse:
    context_id = UUID(request.context_id)
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    resource = await create_text_resource(
        db, owner_id=learner.id, context_id=context_id, title=request.title, text=request.text
    )
    return resource_response(db, resource)


@router.post("/pdf", response_model=ResourceResponse, status_code=201)
async def add_pdf_resource(
    learner: CurrentLearner,
    db: Db,
    request: Request,
    context_id: str,
    title: str = "Uploaded PDF",
) -> ResourceResponse:
    context_uuid = UUID(context_id)
    ensure_context(db, context_id=context_uuid, owner_id=learner.id)
    content = await read_upload_body(request)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty PDF upload")
    resource = await create_pdf_resource(
        db,
        owner_id=learner.id,
        context_id=context_uuid,
        title=title,
        content=content,
    )
    return resource_response(db, resource)


@router.get("", response_model=list[ResourceResponse])
def list_resources(learner: CurrentLearner, db: Db, context_id: str) -> list[ResourceResponse]:
    context_uuid = UUID(context_id)
    ensure_context(db, context_id=context_uuid, owner_id=learner.id)
    resources = db.scalars(
        select(Resource).where(Resource.owner_id == learner.id, Resource.context_id == context_uuid)
    ).all()
    return [resource_response(db, resource) for resource in resources]


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource_detail(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    return resource_response(db, resource)


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
    ).all()
    return [
        ChunkResponse(chunk_index=chunk.chunk_index, content=chunk.content)
        for chunk in chunks[:3]
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
    return resource_response(db, processed)


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
    return resource_response(db, replaced)


@router.put("/{resource_id}/pdf", response_model=ResourceResponse)
async def replace_pdf(
    resource_id: UUID,
    learner: CurrentLearner,
    db: Db,
    request: Request,
    title: str = "Uploaded PDF",
) -> ResourceResponse:
    resource = get_resource(db, resource_id=resource_id, owner_id=learner.id)
    content = await read_upload_body(request)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty PDF upload")
    replaced = await replace_pdf_resource(
        db, resource=resource, title=title, content=content
    )
    return resource_response(db, replaced)
