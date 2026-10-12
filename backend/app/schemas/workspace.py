"""Workspace Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBase(BaseModel):
    """Base workspace properties."""
    title: str = Field(..., min_length=1, max_length=255, description="Title of the workspace")
    description: Optional[str] = Field(None, description="Optional description of the workspace")


class WorkspaceCreate(WorkspaceBase):
    """Payload for creating a workspace."""
    pass


class WorkspaceResponse(WorkspaceBase):
    """Schema returned for a workspace entity."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


class WorkspaceDetailResponse(WorkspaceResponse):
    """Schema returned when viewing workspace details with documents."""
    pass
