"""Evaluation schemas for benchmark runs and metric reporting."""

from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvaluationCaseResult(BaseModel):
    """Result of an individual benchmark evaluation test case."""

    id: str
    type: str  # POSITIVE, NEGATIVE, INJECTION
    query: str
    status: str  # PASS, FAIL
    retrieval_hit: Optional[bool] = None
    is_abstained: bool
    citation_valid: bool
    notes: Optional[str] = None
    latency_ms: float = 0.0


class EvaluationRunRequest(BaseModel):
    """Request payload to trigger an evaluation benchmark run."""

    suite_name: str = Field(default="ProofLens Benchmark Suite v1", max_length=128)


class EvaluationRunResponse(BaseModel):
    """Summary and details of an evaluation run."""

    id: UUID
    workspace_id: UUID
    suite_name: str
    total_cases: int
    passed_cases: int
    retrieval_hit_rate: float
    citation_validity_rate: float
    abstention_accuracy: float
    raw_results: Dict[str, Any]
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
