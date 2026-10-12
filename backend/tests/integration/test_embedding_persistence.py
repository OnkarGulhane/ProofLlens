"""Integration tests verifying end-to-end chunking and vector persistence in pgvector."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.chunk import DocumentChunk
from app.services.embedding_service import get_embedding_provider
from tests.pdf_helpers import create_synthetic_pdf


@pytest.mark.asyncio
async def test_document_upload_persists_chunks_and_embeddings(async_client: AsyncClient):
    """
    Verifies that uploading a PDF automatically chunks pages, generates embeddings,
    persists vectors in PostgreSQL pgvector, and allows vector distance queries.
    """
    # 1. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Vector Persistence Workspace"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Upload 2-page document with distinct content
    p1 = "Operating revenue in Q3 reached fourteen million dollars with strong margin expansion."
    p2 = "Capital expenditures were focused on infrastructure and cloud server scaling."
    pdf_bytes = create_synthetic_pdf([p1, p2])

    upload_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("earnings_report.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["chunk_count"] >= 2

    # 3. Verify chunks and embeddings in PostgreSQL database
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await session.execute(stmt)
        chunks = list(result.scalars().all())

        assert len(chunks) >= 2
        # Verify page provenance
        page_numbers = {c.page_number for c in chunks}
        assert 1 in page_numbers
        assert 2 in page_numbers

        # Verify embedding vectors are 1536-dimensional
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1536

        # 4. Perform vector similarity search using pgvector cosine_distance (<=>)
        provider = get_embedding_provider()
        query_text = "What was the operating revenue in Q3?"
        query_vec = await provider.embed_query(query_text)

        search_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.workspace_id == ws_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vec))
            .limit(1)
        )
        search_res = await session.execute(search_stmt)
        top_chunk = search_res.scalar_one_or_none()

        assert top_chunk is not None
        assert top_chunk.page_number == 1
        assert "fourteen million" in top_chunk.content

    # 5. Verify cascade deletion of chunks
    del_res = await async_client.delete(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}")
    assert del_res.status_code == 204

    async with AsyncSessionLocal() as session:
        check_stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        check_res = await session.execute(check_stmt)
        assert len(list(check_res.scalars().all())) == 0
