"""Document and DocumentPage Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class DocumentPageResponse(BaseModel):
    """Schema for extracted document page text."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    character_count: int
    raw_text: str
    created_at: datetime


class DocumentResponse(BaseModel):
    """Schema for document metadata and ingestion status."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    file_size_bytes: int
    total_pages: int
    chunk_count: int = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Schema for document entity including extracted pages."""
    pages: List[DocumentPageResponse] = []
