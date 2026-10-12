"""Unit tests for Server-Side Citation Validation."""

import uuid
import pytest
from app.services.citation_service import CitationService, ParsedCitation
from app.services.retrieval_service import RetrievedChunk


def test_citation_parsing():
    """Verify regex extraction of [Doc: ..., Page: ...] markers."""
    text = (
        "Operating revenue increased by 14% YoY [Doc: earnings_report.pdf, Page: 4]. "
        "Cloud expenditures also rose significantly [Document: infra_budget.pdf, Page: 12]."
    )
    citations = CitationService.parse_citations(text)

    assert len(citations) == 2
    assert citations[0].document_name == "earnings_report.pdf"
    assert citations[0].page_number == 4
    assert citations[1].document_name == "infra_budget.pdf"
    assert citations[1].page_number == 12


def test_citation_verification_against_candidate_chunks():
    """Verify that citations matching retrieved chunks are VERIFIED and hallucinations are UNVERIFIED."""
    c_id = uuid.uuid4()
    d_id = uuid.uuid4()
    candidate_chunks = [
        RetrievedChunk(
            chunk_id=c_id,
            document_id=d_id,
            document_name="annual_report.pdf",
            page_number=3,
            chunk_index=0,
            content="Operating profit margin was 21 percent.",
            similarity_score=0.91,
            rank=1,
        )
    ]

    # Citation 1: Valid (matches annual_report.pdf, Page 3)
    # Citation 2: Hallucination (invented Page 99)
    # Citation 3: Hallucination (invented file fake.pdf)
    parsed = [
        ParsedCitation("annual_report.pdf", 3, "[Doc: annual_report.pdf, Page: 3]"),
        ParsedCitation("annual_report.pdf", 99, "[Doc: annual_report.pdf, Page: 99]"),
        ParsedCitation("fake_paper.pdf", 1, "[Doc: fake_paper.pdf, Page: 1]"),
    ]

    verified, unverified = CitationService.validate_citations(parsed, candidate_chunks)

    assert len(verified) == 1
    assert verified[0].chunk_id == c_id
    assert verified[0].page_number == 3
    assert verified[0].verification_status == "VERIFIED"

    assert len(unverified) == 2
    assert unverified[0].page_number == 99
    assert unverified[1].document_name == "fake_paper.pdf"


def test_sanitize_answer_text_strips_hallucinations():
    """Verify that unverified citation markers are scrubbed from user-facing answer text."""
    text = "Valid claim [Doc: real.pdf, Page: 1] but fake claim [Doc: fake.pdf, Page: 99]."
    unverified = [ParsedCitation("fake.pdf", 99, "[Doc: fake.pdf, Page: 99]")]

    sanitized = CitationService.sanitize_answer_text(text, unverified)
    assert "[Doc: real.pdf, Page: 1]" in sanitized
    assert "[Doc: fake.pdf, Page: 99]" not in sanitized
