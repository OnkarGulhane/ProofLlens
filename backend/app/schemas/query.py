"""Grounded Q&A and Citation Pydantic schemas."""

import uuid
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.retrieval import RetrievedChunkResponse


class QueryRequest(BaseModel):
    """Payload for submitting a grounded question to a workspace."""
    question: str = Field(..., min_length=1, description="Question text to answer based on documents")
    document_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional document ID filters")
    similarity_threshold: float = Field(0.65, ge=0.0, le=1.0, description="Minimum similarity cutoff")
    top_k: int = Field(5, ge=1, le=20, description="Number of evidence chunks to retrieve")


class CitationDTO(BaseModel):
    """Schema for a verified citation anchoring an answer to evidence."""
    citation_id: uuid.UUID
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    cited_excerpt: str
    verification_status: str  # VERIFIED, PARTIAL, UNVERIFIED


class QueryResponse(BaseModel):
    """Schema returned for a grounded Q&A execution."""
    query_run_id: uuid.UUID
    workspace_id: uuid.UUID
    question: str
    answer: str
    is_abstained: bool
    abstention_reason: Optional[str] = None
    citations: List[CitationDTO] = []
    retrieved_evidence: List[RetrievedChunkResponse] = []
