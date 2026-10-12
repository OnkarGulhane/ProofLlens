"""Unit tests for the Sliding-Window Chunking Engine."""

import pytest
from app.services.chunking_service import ChunkingService


def test_chunk_single_page_short_text():
    """Verify that a short page produces a single chunk containing all content."""
    text = "ProofLens AI provides evidence-first verifiable answers."
    chunks = ChunkingService.chunk_page_text(text=text, page_number=1, start_chunk_index=0)

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == text
    assert chunks[0].token_count > 0


def test_chunk_sliding_window_overlap():
    """Verify that long text is segmented into overlapping chunks with appropriate window step."""
    # Create 1200 character text
    base_sentence = "This is a detailed factual statement about evidence grounding in document retrieval. "
    long_text = base_sentence * 15  # ~1300 characters
    chunk_size = 300
    chunk_overlap = 50

    chunks = ChunkingService.chunk_page_text(
        text=long_text,
        page_number=1,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    assert len(chunks) > 1
    for i in range(len(chunks) - 1):
        # Verify consecutive chunks have overlapping content
        current_chunk = chunks[i].content
        next_chunk = chunks[i + 1].content
        # Find some shared words
        current_words = set(current_chunk.split()[-5:])
        next_words = set(next_chunk.split()[:5])
        assert len(current_words.intersection(next_words)) > 0


def test_page_boundary_strict_isolation():
    """Verify that chunks NEVER cross page boundaries."""
    page_1 = "Content of first page with specific claims about Q1 revenue and operating expenses."
    page_2 = "Content of second page discussing balance sheet liabilities and audit notes."

    pages = [(1, page_1), (2, page_2)]
    all_chunks = ChunkingService.chunk_document_pages(pages, chunk_size=200, chunk_overlap=30)

    # Every chunk must belong strictly to page 1 or page 2
    for chunk in all_chunks:
        if chunk.page_number == 1:
            assert "first page" in chunk.content
            assert "second page" not in chunk.content
        elif chunk.page_number == 2:
            assert "second page" in chunk.content
            assert "first page" not in chunk.content

    # Indices must be sequential: 0, 1, ...
    indices = [c.chunk_index for c in all_chunks]
    assert indices == list(range(len(all_chunks)))


def test_empty_or_whitespace_page():
    """Verify that empty or blank pages produce zero chunks."""
    chunks = ChunkingService.chunk_page_text(text="   \n\n\t   ", page_number=1)
    assert len(chunks) == 0
