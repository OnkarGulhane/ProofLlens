"""Semantic Retrieval Service backed by pgvector cosine similarity search."""

import time
import uuid
from typing import List, Optional, NamedTuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import get_embedding_provider, EmbeddingProvider


class RetrievedChunk(NamedTuple):
    """Represents a candidate chunk retrieved and ranked by vector similarity."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity_score: float
    rank: int


class RetrievalService:
    """Orchestrates query embedding, vector similarity search, and relevance threshold filtering."""

    @classmethod
    async def retrieve_chunks(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        document_ids: Optional[List[uuid.UUID]] = None,
        similarity_threshold: float = 0.65,
        top_k: int = 5,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes semantic vector search across document chunks within a workspace.
        Returns:
            Ranked list of RetrievedChunk items with similarity >= similarity_threshold.
        """
        start_time = time.perf_counter()
        provider = embedding_provider or get_embedding_provider()

        # 1. Generate query embedding
        query_vector = await provider.embed_query(query)

        # 2. Compute similarity: 1 - cosine_distance
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)
        similarity_expr = 1.0 - distance_expr

        # 3. Build query filters
        filters = [
            DocumentChunk.workspace_id == workspace_id,
            similarity_expr >= similarity_threshold,
        ]

        if document_ids and len(document_ids) > 0:
            filters.append(DocumentChunk.document_id.in_(document_ids))

        # 4. Query matching chunks joined with Document to obtain filename
        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.filename,
                DocumentChunk.page_number,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                similarity_expr.label("similarity_score"),
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(and_(*filters))
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        retrieved: List[RetrievedChunk] = []
        for index, row in enumerate(rows):
            chunk_id, doc_id, doc_name, page_num, chunk_idx, content, score = row
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    document_name=doc_name,
                    page_number=page_num,
                    chunk_index=chunk_idx,
                    content=content,
                    similarity_score=round(float(score), 4),
                    rank=index + 1,
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Semantic retrieval for workspace {workspace_id} found {len(retrieved)} chunks "
            f"in {elapsed_ms:.2f}ms (threshold={similarity_threshold}, top_k={top_k})."
        )
        return retrieved
