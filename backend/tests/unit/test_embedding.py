"""Unit tests for the Embedding Service."""

import math
import pytest
from app.services.embedding_service import MockEmbeddingProvider, get_embedding_provider


@pytest.mark.asyncio
async def test_mock_embedding_provider_properties():
    """Verify that MockEmbeddingProvider generates normalized 1536-dimensional vectors."""
    provider = MockEmbeddingProvider(dimension=1536)
    assert provider.dimension == 1536

    texts = [
        "First document text about financial performance.",
        "Second text about machine learning embeddings.",
    ]
    vectors = await provider.embed_texts(texts)

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == 1536
        # Verify L2 normalization: sum of squares ≈ 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        assert pytest.approx(norm, rel=1e-5) == 1.0


@pytest.mark.asyncio
async def test_mock_embedding_determinism():
    """Verify that identical inputs produce identical embeddings (deterministic)."""
    provider = MockEmbeddingProvider(dimension=1536)
    text = "Deterministic embedding test string."

    v1 = await provider.embed_query(text)
    v2 = await provider.embed_query(text)

    assert v1 == v2

    different_vec = await provider.embed_query("Completely unrelated text string.")
    assert v1 != different_vec


def test_embedding_factory():
    """Verify that the factory function returns a valid EmbeddingProvider instance."""
    provider = get_embedding_provider()
    assert provider.dimension == 1536
