"""EvaluationRun ORM model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class EvaluationRun(Base):
    """Represents a benchmark test suite execution with quantitative scores."""

    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_name = Column(String(128), nullable=False)
    total_cases = Column(Integer, nullable=False)
    passed_cases = Column(Integer, nullable=False)
    retrieval_hit_rate = Column(Float, nullable=False)
    citation_validity_rate = Column(Float, nullable=False)
    abstention_accuracy = Column(Float, nullable=False)
    raw_results = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    workspace = relationship("Workspace", back_populates="evaluation_runs")
