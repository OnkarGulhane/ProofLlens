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

    def _generate_word_vector(self, word: str) -> List[float]:
        """Generates an unnormalized random Gaussian vector seeded deterministically by word token."""
        seed_int = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed_int)
        return [rng.gauss(0.0, 1.0) for _ in range(self._dimension)]

    def _generate_deterministic_vector(self, text: str) -> List[float]:
        """Generates an L2-normalized float vector based deterministically on input text tokens."""
        import re
        stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
            "is", "are", "was", "were", "what", "who", "how", "it", "its"
        }
        raw_tokens = re.findall(r"\w+", text.lower())
        tokens = [w.rstrip("s") for w in raw_tokens if w not in stop_words]
        if not tokens:
            tokens = ["empty"]

        base_vec = self._generate_word_vector("__english_base_semantic__")
        scale = 0.5 * math.sqrt(len(tokens))

        acc = [scale * base_vec[i] for i in range(self._dimension)]
        for word in tokens:
            w_vec = self._generate_word_vector(word)
            for i in range(self._dimension):
                acc[i] += w_vec[i]

        # L2-normalize vector to unit length
        squared_sum = sum(x * x for x in acc)
        norm = math.sqrt(squared_sum) if squared_sum > 0 else 1.0

        return [x / norm for x in acc]

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


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Generates dense vector embeddings using Google Gemini text-embedding-004."""

    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY
        self._model = settings.GEMINI_EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIMENSIONS
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def dimension(self) -> int:
        return self._dim

    def _normalize_and_pad(self, vector: List[float]) -> List[float]:
        """Ensures vector is unit-normalized and matches target dimensionality."""
        if len(vector) > self._dim:
            vector = vector[: self._dim]
        elif len(vector) < self._dim:
            vector = vector + [0.0] * (self._dim - len(vector))

        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            return [x / norm for x in vector]
        return vector

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Calls Google Gemini batchEmbedContents API."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents"
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        batch_size = 50
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            requests = [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": t}]},
                    "outputDimensionality": self._dim,
                }
                for t in batch
            ]
            payload = {"requests": requests}
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_embeddings = data.get("embeddings", [])
            for item in raw_embeddings:
                all_embeddings.append(self._normalize_and_pad(item.get("values", [])))

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query string."""
        results = await self.embed_texts([query])
        return results[0]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function providing the configured embedding provider."""
    if settings.GEMINI_API_KEY and (settings.LLM_PROVIDER.lower() == "gemini" or not settings.OPENAI_API_KEY):
        logger.info(f"Using GeminiEmbeddingProvider ({settings.GEMINI_EMBEDDING_MODEL})")
        return GeminiEmbeddingProvider()

    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        logger.info(f"Using OpenAIEmbeddingProvider ({settings.EMBEDDING_MODEL})")
        return OpenAIEmbeddingProvider()

    logger.info("No external AI keys set or valid; using MockEmbeddingProvider for offline operation.")
    return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSIONS)
