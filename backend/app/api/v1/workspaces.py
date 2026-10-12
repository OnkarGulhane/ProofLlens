"""Workspace API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.exceptions import WorkspaceNotFoundError
from app.models.workspace import Workspace
from app.models.document import Document
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceDetailResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    session: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Creates a new logical workspace for document investigation."""
    workspace = Workspace(
        title=payload.title,
        description=payload.description,
    )
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceResponse(
        id=workspace.id,
        title=workspace.title,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        document_count=0,
    )


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Workspaces",
)
async def list_workspaces(
    session: AsyncSession = Depends(get_db),
) -> List[WorkspaceResponse]:
    """Retrieves all workspaces along with their document counts."""
    stmt = (
        select(Workspace, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Workspace.id == Document.workspace_id)
        .group_by(Workspace.id)
        .order_by(Workspace.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    workspaces: List[WorkspaceResponse] = []
    for ws, doc_count in rows:
        workspaces.append(
            WorkspaceResponse(
                id=ws.id,
                title=ws.title,
                description=ws.description,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
                document_count=doc_count,
            )
        )
    return workspaces


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Details",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> WorkspaceDetailResponse:
    """Retrieves details of a specific workspace."""
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise WorkspaceNotFoundError(str(workspace_id))

    # Count documents
    count_stmt = select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
    count_res = await session.execute(count_stmt)
    doc_count = count_res.scalar_one()

    return WorkspaceDetailResponse(
        id=workspace.id,
        title=workspace.title,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        document_count=doc_count,
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Workspace",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Deletes a workspace and all cascading child records."""
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise WorkspaceNotFoundError(str(workspace_id))

    await session.delete(workspace)
    await session.commit()
    return None

