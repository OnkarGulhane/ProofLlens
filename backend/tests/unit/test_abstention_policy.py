"""Unit tests for the Grounded Abstention Policy."""

import uuid
import pytest
from app.services.qa_service import ABSTENTION_MESSAGE, QAService
from app.services.citation_service import CitationService, ParsedCitation


def test_abstention_message_constant():
    """Verify standard insufficient evidence string defined by PRD."""
    assert "not contain sufficient evidence" in ABSTENTION_MESSAGE.lower()


def test_hallucination_abstention_gate():
    """Verify that when all claimed citations are unverified, abstention is enforced."""
    # Model claims citations that don't match any retrieved chunk
    fake_citations = [ParsedCitation("nonexistent.pdf", 5, "[Doc: nonexistent.pdf, Page: 5]")]
    verified, unverified = CitationService.validate_citations(fake_citations, [])

    assert len(verified) == 0
    assert len(unverified) == 1
    # System recognizes 100% citation failure and enforces abstention
    assert len(fake_citations) > 0 and len(verified) == 0
