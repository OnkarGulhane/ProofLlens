"""Health and operational readiness check endpoints."""

import os
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    project: str
    version: str
    environment: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    """Readiness probe response schema."""
    status: str
    checks: Dict[str, Any]
    timestamp: datetime


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Probe",
)
async def get_health() -> HealthResponse:
    """Returns basic liveness information about the ProofLens API server."""
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Readiness Probe",
)
async def get_ready() -> ReadyResponse:
    """Returns operational readiness of the application components."""
    from app.core.database import check_database_connection
    storage_accessible = os.path.exists(settings.STORAGE_DIR) or os.makedirs(settings.STORAGE_DIR, exist_ok=True) is None
    db_connected = await check_database_connection()

    checks = {
        "configuration": "loaded",
        "storage": "accessible" if storage_accessible else "unavailable",
        "database": "connected" if db_connected else "unreachable",
    }

    return ReadyResponse(
        status="ready" if (storage_accessible and db_connected) else "degraded",
        checks=checks,
        timestamp=datetime.now(timezone.utc),
    )
