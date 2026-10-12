"""Unit tests for Retrieval Service logic."""

import uuid
import pytest
from app.services.retrieval_service import RetrievedChunk


def test_retrieved_chunk_properties():
    """Verify RetrievedChunk data structure fields and formatting."""
    c_id = uuid.uuid4()
    d_id = uuid.uuid4()

    chunk = RetrievedChunk(
        chunk_id=c_id,
        document_id=d_id,
        document_name="annual_report.pdf",
        page_number=4,
        chunk_index=2,
        content="Operating revenue grew by 18 percent.",
        similarity_score=0.8842,
        rank=1,
    )

    assert chunk.chunk_id == c_id
    assert chunk.document_id == d_id
    assert chunk.document_name == "annual_report.pdf"
    assert chunk.page_number == 4
    assert chunk.similarity_score == 0.8842
    assert chunk.rank == 1
