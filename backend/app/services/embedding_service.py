"""Embedding Service Interface and Provider Implementations."""

import abc
import hashlib
import math
import random
from typing import List
import httpx
from app.core.config import settings
from app.core.logging import logger


class EmbeddingProvider(abc.ABC):
    """Abstract base class for vector embedding generation providers."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Returns the dimensionality of vectors produced by this provider."""
        pass

    @abc.abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text chunks."""
        pass

    @abc.abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generates an embedding for a search query string."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic pseudo-embedding generator producing unit-normalized 1536-dim vectors.
    Enables reproducible, offline local development and test suite execution without API costs.
    """

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_deterministic_vector(self, text: str) -> List[float]:
        """Generates an L2-normalized float vector based deterministically on input text."""
        seed_int = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed_int)

        # Generate base random components
        raw_vector = [rng.gauss(0.0, 1.0) for _ in range(self._dimension)]

        # L2-normalize vector to unit length
        squared_sum = sum(x * x for x in raw_vector)
        norm = math.sqrt(squared_sum) if squared_sum > 0 else 1.0

        return [x / norm for x in raw_vector]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates deterministic embeddings for a batch of texts."""
        return [self._generate_deterministic_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        """Generates a deterministic embedding for a search query."""
        return self._generate_deterministic_vector(query)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Generates dense vector embeddings using OpenAI text-embedding-3-small."""

    def __init__(self):
        self._api_key = settings.OPENAI_API_KEY
        self._model = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIMENSIONS
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Calls OpenAI /v1/embeddings in batches of up to 100 items."""
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Process in batches of 100
        batch_size = 100
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "input": batch,
                "model": self._model,
            }
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Sort embeddings by index to preserve input ordering
            sorted_data = sorted(data["data"], key=lambda item: item["index"])
            all_embeddings.extend([item["embedding"] for item in sorted_data])

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string."""
        results = await self.embed_texts([query])
        return results[0]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function providing the configured embedding provider."""
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        logger.info(f"Using OpenAIEmbeddingProvider ({settings.EMBEDDING_MODEL})")
        return OpenAIEmbeddingProvider()

    logger.info("OPENAI_API_KEY not set or invalid; using MockEmbeddingProvider for offline operation.")
    return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSIONS)
