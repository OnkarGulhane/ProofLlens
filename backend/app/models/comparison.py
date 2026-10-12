"""ComparisonRun ORM model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComparisonRun(Base):
    """Represents a cross-document comparative analysis run."""

    __tablename__ = "comparison_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(Text, nullable=False)
    document_ids = Column(JSONB, nullable=False)
    comparison_matrix = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    workspace = relationship("Workspace", back_populates="comparison_runs")
