"""Unit tests for configuration loading and validation."""

from app.core.config import Settings


def test_default_settings():
    """Verify that default settings instantiate with expected values."""
    test_settings = Settings()
    assert test_settings.PROJECT_NAME == "ProofLens AI"
    assert test_settings.PORT == 8000
    assert test_settings.API_V1_STR == "/api/v1"
    assert test_settings.MAX_UPLOAD_SIZE_BYTES == 10 * 1024 * 1024
    assert test_settings.EMBEDDING_DIMENSIONS == 1536
    assert isinstance(test_settings.CORS_ORIGINS, list)
