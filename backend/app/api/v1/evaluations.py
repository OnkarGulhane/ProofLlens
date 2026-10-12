"""API endpoints for Quantitative Benchmark Evaluations."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.logging import logger
from app.core.exceptions import WorkspaceNotFoundError
from app.models.evaluation import EvaluationRun
from app.schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/workspaces/{workspace_id}/evaluations", tags=["Evaluations"])


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute quantitative benchmark evaluation suite",
)
async def run_evaluation(
    workspace_id: uuid.UUID,
    payload: EvaluationRunRequest = EvaluationRunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the standard ProofLens benchmark evaluation suite against this workspace.
    Computes Retrieval Hit Rate, Citation Validity Rate, and Negative Abstention Accuracy.
    """
    try:
        eval_run = await EvaluationService.run_evaluation_suite(
            session=db,
            workspace_id=workspace_id,
        )
        return eval_run
    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error running evaluation suite on workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation execution failed: {str(e)}",
        )


@router.get(
    "",
    response_model=List[EvaluationRunResponse],
    summary="List past evaluation runs for a workspace",
)
async def list_evaluations(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all past benchmark runs for the specified workspace."""
    stmt = (
        select(EvaluationRun)
        .where(EvaluationRun.workspace_id == workspace_id)
        .order_by(EvaluationRun.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationRunResponse,
    summary="Get evaluation run details by ID",
)
async def get_evaluation(
    workspace_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetches full results of a specific evaluation run."""
    stmt = select(EvaluationRun).where(
        EvaluationRun.id == evaluation_id,
        EvaluationRun.workspace_id == workspace_id,
    )
    res = await db.execute(stmt)
    eval_run = res.scalar_one_or_none()
    if not eval_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run {evaluation_id} not found in this workspace.",
        )
    return eval_run
