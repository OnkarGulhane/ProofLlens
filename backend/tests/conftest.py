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
def mock_ai_settings(monkeypatch):
    """Ensure pytest tests run with mock AI providers deterministically offline."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")


@pytest.fixture(autouse=True)
async def cleanup_database_engine():
    """Ensure all pooled asyncpg connections are cleanly disposed before event loop teardown."""
    yield
    from app.core.database import engine
    await engine.dispose()


def pytest_sessionfinish(session, exitstatus):
    """Clean up any temporary test workspaces created during test runs."""
    import asyncio

    async def _cleanup():
        from app.core.database import AsyncSessionLocal, engine
        from app.models.workspace import Workspace
        from sqlalchemy import select
        test_titles = {
            "Single Doc Workspace", "Comparison Workspace", "Primary Retrieval Workspace",
            "Abstention Workspace", "Q&A Pipeline Workspace", "Vector Persistence Workspace",
            "Rejection Workspace", "Ingestion Integration Workspace", "Isolated Empty Workspace",
            "Prompt Injection Defense Workspace"
        }
        try:
            async with AsyncSessionLocal() as db_session:
                res = await db_session.execute(select(Workspace).where(Workspace.title.in_(test_titles)))
                for ws in res.scalars().all():
                    await db_session.delete(ws)
                await db_session.commit()
        except Exception:
            pass
        finally:
            await engine.dispose()

    try:
        asyncio.run(_cleanup())
    except Exception:
        pass
