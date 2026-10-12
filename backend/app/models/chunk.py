"""DocumentChunk ORM model with vector embeddings."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Integer, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class DocumentChunk(Base):
    """Represents an isolated text chunk with exact page provenance and dense vector embedding."""

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_chunks_doc_page", "document_id", "page_number"),
    )

    # Relationships
    document = relationship("Document", back_populates="chunks")
    workspace = relationship("Workspace", back_populates="chunks")
    retrieved_evidences = relationship("RetrievedEvidence", back_populates="chunk", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="chunk", cascade="all, delete-orphan")
