"""Integration tests verifying SQLAlchemy models, pgvector, and database operations."""

import uuid
import pytest
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal, check_database_connection
from app.models.workspace import Workspace
from app.models.document import Document, DocumentPage
from app.models.chunk import DocumentChunk
from app.models.query import QueryRun, Answer, Citation


@pytest.mark.asyncio
async def test_database_connectivity():
    """Verify that the database is reachable."""
    is_connected = await check_database_connection()
    assert is_connected is True


@pytest.mark.asyncio
async def test_workspace_and_document_crud_with_cascade():
    """Verify CRUD on Workspace, Document, DocumentPage, and DocumentChunk with cascade deletion."""
    async with AsyncSessionLocal() as session:
        # 1. Create Workspace
        ws_id = uuid.uuid4()
        workspace = Workspace(
            id=ws_id,
            title="Test Integration Workspace",
            description="Testing SQLAlchemy async operations",
        )
        session.add(workspace)
        await session.commit()

        # 2. Add Document and Page
        doc_id = uuid.uuid4()
        document = Document(
            id=doc_id,
            workspace_id=ws_id,
            filename="integration_test.pdf",
            file_path="storage/uploads/test.pdf",
            file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size_bytes=1024,
            total_pages=1,
            status="READY",
        )
        session.add(document)

        page = DocumentPage(
            document_id=doc_id,
            page_number=1,
            raw_text="ProofLens AI provides evidence-first verifiable answers.",
            character_count=56,
        )
        session.add(page)

        # 3. Add Document Chunk with 1536-dimensional embedding vector
        test_vector = [0.01] * 1536
        chunk_id = uuid.uuid4()
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=doc_id,
            workspace_id=ws_id,
            page_number=1,
            chunk_index=0,
            content="ProofLens AI provides evidence-first verifiable answers.",
            token_count=12,
            embedding=test_vector,
        )
        session.add(chunk)
        await session.commit()

        # 4. Verify Chunk can be queried with vector similarity
        query_vector = [0.01] * 1536
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.workspace_id == ws_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        result = await session.execute(stmt)
        matched_chunk = result.scalar_one_or_none()
        assert matched_chunk is not None
        assert matched_chunk.id == chunk_id
        assert matched_chunk.page_number == 1

        # 5. Verify Cascade Deletion: Deleting Workspace deletes Document, Page, and Chunk
        await session.delete(workspace)
        await session.commit()

        # Verify Document is deleted
        doc_check = await session.execute(select(Document).where(Document.id == doc_id))
        assert doc_check.scalar_one_or_none() is None

        # Verify Page is deleted
        page_check = await session.execute(select(DocumentPage).where(DocumentPage.document_id == doc_id))
        assert page_check.scalar_one_or_none() is None

        # Verify Chunk is deleted
        chunk_check = await session.execute(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
        assert chunk_check.scalar_one_or_none() is None
