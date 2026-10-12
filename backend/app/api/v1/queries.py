"""Grounded Question Answering API endpoints."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.query import QueryRequest, QueryResponse
from app.services.qa_service import QAService

router = APIRouter(prefix="/workspaces/{workspace_id}/query", tags=["Q&A"])


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Grounded Question",
)
async def submit_query(
    workspace_id: uuid.UUID,
    payload: QueryRequest,
    session: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Answers a question grounded strictly in workspace document evidence with validated citations."""
    return await QAService.answer_question(
        session=session,
        workspace_id=workspace_id,
        question=payload.question,
        document_ids=payload.document_ids,
        similarity_threshold=payload.similarity_threshold,
        top_k=payload.top_k,
    )
