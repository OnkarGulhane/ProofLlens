"""Cross-Document Comparison Pydantic schemas."""

import uuid
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.query import CitationDTO


class ConsensusStatus(str, Enum):
    """Classification of alignment across compared documents."""
    AGREEMENT = "AGREEMENT"
    DIFFERENCE = "DIFFERENCE"
    CONTRADICTION = "CONTRADICTION"
    INCOMPARABLE = "INCOMPARABLE"


class ComparisonRequest(BaseModel):
    """Payload for submitting a cross-document comparative inquiry."""
    topic: str = Field(..., min_length=1, description="Topic or question to compare across documents")
    document_ids: List[uuid.UUID] = Field(
        ...,
        min_length=2,
        description="List of at least two document UUIDs to compare",
    )


class DocumentFinding(BaseModel):
    """Summarized findings and citations for a single document under comparison."""
    document_id: uuid.UUID
    document_name: str
    summary: str
    citations: List[CitationDTO] = []


class ComparisonSynthesis(BaseModel):
    """High-level synthesis and consensus classification across documents."""
    consensus: ConsensusStatus
    analysis: str


class ComparisonResponse(BaseModel):
    """Response returned for a cross-document comparison run."""
    comparison_run_id: uuid.UUID
    workspace_id: uuid.UUID
    topic: str
    documents_analyzed: List[uuid.UUID]
    findings: List[DocumentFinding]
    synthesis: ComparisonSynthesis
