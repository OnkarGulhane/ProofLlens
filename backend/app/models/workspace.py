"""Workspace ORM model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Workspace(Base):
    """Represents a logical workspace containing documents and queries."""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="workspace", cascade="all, delete-orphan")
    query_runs = relationship("QueryRun", back_populates="workspace", cascade="all, delete-orphan")
    comparison_runs = relationship("ComparisonRun", back_populates="workspace", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="workspace", cascade="all, delete-orphan")
