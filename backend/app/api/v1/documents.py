"""Document upload and management API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentDetailResponse, DocumentPageResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest PDF Document",
)
async def upload_document(
    workspace_id: uuid.UUID,
    file: UploadFile = File(..., description="PDF document to upload and ingest"),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Uploads a PDF, validates its format and text layer, extracts pages, and stores it."""
    file_bytes = await file.read()
    filename = file.filename or "uploaded_document.pdf"

    document = await DocumentService.process_and_store_document(
        session=session,
        workspace_id=workspace_id,
        filename=filename,
        content=file_bytes,
    )

    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Documents in Workspace",
)
async def list_documents(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Retrieves all documents belonging to the workspace."""
    documents = await DocumentService.list_documents(session, workspace_id)
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Details with Pages",
)
async def get_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Retrieves a document with its extracted page contents."""
    stmt = (
        select(Document)
        .options(selectinload(Document.pages))
        .where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    result = await session.execute(stmt)
    document = result.scalar_one_or_none()
    if not document:
        raise DocumentNotFoundError(str(document_id))

    return DocumentDetailResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        total_pages=document.total_pages,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        pages=[
            DocumentPageResponse(
                id=p.id,
                page_number=p.page_number,
                character_count=p.character_count,
                raw_text=p.raw_text,
                created_at=p.created_at,
            )
            for p in document.pages
        ],
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
)
async def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a document from the workspace and deletes its physical file from disk."""
    await DocumentService.delete_document(session, workspace_id, document_id)
