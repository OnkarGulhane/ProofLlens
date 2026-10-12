"""DocumentChunk Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentChunkResponse(BaseModel):
    """Schema for a text chunk with provenance metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    page_number: int
    chunk_index: int
    content: str
    token_count: int
    created_at: datetime
