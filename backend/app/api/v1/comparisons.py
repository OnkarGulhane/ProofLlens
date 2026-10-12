"""Cross-Document Comparison API endpoints."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/workspaces/{workspace_id}/compare", tags=["Comparison"])


@router.post(
    "",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Cross-Document Comparative Analysis",
)
async def compare_documents(
    workspace_id: uuid.UUID,
    payload: ComparisonRequest,
    session: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Performs side-by-side evidence extraction and consensus analysis across multiple documents."""
    return await ComparisonService.compare_documents(
        session=session,
        workspace_id=workspace_id,
        topic=payload.topic,
        document_ids=payload.document_ids,
    )
