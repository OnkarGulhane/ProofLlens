"""Unit tests for Cross-Document Comparison schema and logic."""

import uuid
import pytest
from pydantic import ValidationError
from app.schemas.comparison import ConsensusStatus, ComparisonRequest, ComparisonSynthesis


def test_consensus_status_enum():
    """Verify supported consensus categories defined by PRD."""
    assert ConsensusStatus.AGREEMENT == "AGREEMENT"
    assert ConsensusStatus.DIFFERENCE == "DIFFERENCE"
    assert ConsensusStatus.CONTRADICTION == "CONTRADICTION"
    assert ConsensusStatus.INCOMPARABLE == "INCOMPARABLE"


def test_comparison_request_enforces_minimum_two_documents():
    """Verify that submitting fewer than two documents raises validation error."""
    doc_id = uuid.uuid4()

    # Valid with 2 documents
    req = ComparisonRequest(topic="Revenue", document_ids=[doc_id, uuid.uuid4()])
    assert len(req.document_ids) == 2

    # Invalid with 1 document
    with pytest.raises(ValidationError):
        ComparisonRequest(topic="Revenue", document_ids=[doc_id])

    # Invalid with empty list
    with pytest.raises(ValidationError):
        ComparisonRequest(topic="Revenue", document_ids=[])
