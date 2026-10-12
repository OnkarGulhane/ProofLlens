"""Semantic Retrieval API endpoints."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import WorkspaceNotFoundError
from app.models.workspace import Workspace
from app.schemas.retrieval import (
    RetrievalQueryRequest,
    RetrievedChunkResponse,
    RetrievalQueryResponse,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/workspaces/{workspace_id}/retrieve", tags=["Retrieval"])


@router.post(
    "",
    response_model=RetrievalQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Vector Retrieval",
)
async def retrieve_chunks(
    workspace_id: uuid.UUID,
    payload: RetrievalQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> RetrievalQueryResponse:
    """Executes semantic cosine similarity search against indexed document chunks."""
    # Verify workspace exists
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
    ws_res = await session.execute(ws_stmt)
    if not ws_res.scalar_one_or_none():
        raise WorkspaceNotFoundError(str(workspace_id))

    retrieved = await RetrievalService.retrieve_chunks(
        session=session,
        workspace_id=workspace_id,
        query=payload.query,
        document_ids=payload.document_ids,
        similarity_threshold=payload.similarity_threshold,
        top_k=payload.top_k,
    )

    chunks_response = [
        RetrievedChunkResponse(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_name=c.document_name,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            content=c.content,
            similarity_score=c.similarity_score,
            rank=c.rank,
        )
        for c in retrieved
    ]

    return RetrievalQueryResponse(
        workspace_id=workspace_id,
        query=payload.query,
        total_found=len(chunks_response),
        retrieved_chunks=chunks_response,
    )
