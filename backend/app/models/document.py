"""Document and DocumentPage ORM models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    """Represents an uploaded source PDF document with processing metadata."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, PARSING, INDEXING, READY, FAILED, UNSUPPORTED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    """Represents raw extracted text for a specific physical page of a document."""

    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)  # 1-indexed physical page
    raw_text = Column(Text, nullable=False)
    character_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_doc_page_number"),
    )

    # Relationships
    document = relationship("Document", back_populates="pages")
