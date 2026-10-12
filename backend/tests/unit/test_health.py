"""Unit tests for the health and ready endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(async_client: AsyncClient):
    """Test that /api/v1/health returns HTTP 200 OK with expected payload."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "ProofLens AI"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_check_returns_200(async_client: AsyncClient):
    """Test that /api/v1/ready returns HTTP 200 OK with readiness checks."""
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["configuration"] == "loaded"
    assert data["checks"]["storage"] == "accessible"
    assert "timestamp" in data
