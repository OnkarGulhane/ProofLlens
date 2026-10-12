"""Semantic Retrieval Pydantic schemas."""

import uuid
from typing import Optional, List
from pydantic import BaseModel, Field


class RetrievalQueryRequest(BaseModel):
    """Payload for executing a semantic retrieval query."""
    query: str = Field(..., min_length=1, description="Search query string")
    document_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional document ID filters")
    similarity_threshold: float = Field(0.65, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of candidate chunks to retrieve")


class RetrievedChunkResponse(BaseModel):
    """Schema for a single retrieved chunk with provenance and similarity ranking."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity_score: float
    rank: int


class RetrievalQueryResponse(BaseModel):
    """Schema for retrieval search results."""
    workspace_id: uuid.UUID
    query: str
    total_found: int
    retrieved_chunks: List[RetrievedChunkResponse]
