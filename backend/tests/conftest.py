"""Pytest configuration and shared fixtures for backend tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    """Async HTTP test client fixture for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
async def cleanup_database_engine():
    """Ensure all pooled asyncpg connections are cleanly disposed before event loop teardown."""
    yield
    from app.core.database import engine
    await engine.dispose()
