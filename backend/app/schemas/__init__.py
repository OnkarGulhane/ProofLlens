"""Pydantic schemas package."""

from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceDetailResponse,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentPageResponse,
    DocumentDetailResponse,
)

__all__ = [
    "WorkspaceCreate",
    "WorkspaceResponse",
    "WorkspaceDetailResponse",
    "DocumentResponse",
    "DocumentPageResponse",
    "DocumentDetailResponse",
]
