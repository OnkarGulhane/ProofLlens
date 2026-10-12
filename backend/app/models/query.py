"""QueryRun, Answer, RetrievedEvidence, and Citation ORM models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class QueryRun(Base):
    """Represents an execution of a user question against a workspace."""

    __tablename__ = "query_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    selected_document_ids = Column(JSONB, nullable=True)
    similarity_threshold = Column(Float, nullable=False, default=0.65)
    top_k = Column(Integer, nullable=False, default=5)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    workspace = relationship("Workspace", back_populates="query_runs")
    answer = relationship("Answer", back_populates="query_run", uselist=False, cascade="all, delete-orphan")
    retrieved_evidences = relationship("RetrievedEvidence", back_populates="query_run", cascade="all, delete-orphan", order_by="RetrievedEvidence.rank")


class Answer(Base):
    """Represents the generated answer and abstention state for a query."""

    __tablename__ = "answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    query_run_id = Column(UUID(as_uuid=True), ForeignKey("query_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    answer_text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="SUCCESS")  # SUCCESS, ABSTAINED, FAILED
    is_abstained = Column(Boolean, nullable=False, default=False)
    abstention_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query_run = relationship("QueryRun", back_populates="answer")
    citations = relationship("Citation", back_populates="answer", cascade="all, delete-orphan")


class RetrievedEvidence(Base):
    """Records each candidate chunk retrieved during similarity search."""

    __tablename__ = "retrieved_evidences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_run_id = Column(UUID(as_uuid=True), ForeignKey("query_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query_run = relationship("QueryRun", back_populates="retrieved_evidences")
    chunk = relationship("DocumentChunk", back_populates="retrieved_evidences")


class Citation(Base):
    """Represents an explicit, verified source citation anchoring an answer to evidence."""

    __tablename__ = "citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    cited_excerpt = Column(Text, nullable=False)
    verification_status = Column(String(32), nullable=False, default="VERIFIED")  # VERIFIED, PARTIAL, UNVERIFIED
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    answer = relationship("Answer", back_populates="citations")
    chunk = relationship("DocumentChunk", back_populates="citations")
    document = relationship("Document", back_populates="citations")
