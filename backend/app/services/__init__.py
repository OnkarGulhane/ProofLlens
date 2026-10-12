"""ProofLens Domain Services Package."""

from app.services.document_service import DocumentService
from app.services.chunking_service import ChunkingService, ChunkItem
from app.services.embedding_service import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)
from app.services.retrieval_service import RetrievalService, RetrievedChunk
from app.services.citation_service import (
    CitationService,
    ParsedCitation,
    VerifiedCitation,
)
from app.services.qa_service import (
    QAService,
    LLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
    ABSTENTION_MESSAGE,
)

__all__ = [
    "DocumentService",
    "ChunkingService",
    "ChunkItem",
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedding_provider",
    "RetrievalService",
    "RetrievedChunk",
    "CitationService",
    "ParsedCitation",
    "VerifiedCitation",
    "QAService",
    "LLMProvider",
    "MockLLMProvider",
    "OpenAILLMProvider",
    "get_llm_provider",
    "ABSTENTION_MESSAGE",
]
