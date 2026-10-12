"""Chunking Engine with strict page isolation and sliding-window segmentation."""

from typing import List, NamedTuple
from app.core.logging import logger


class ChunkItem(NamedTuple):
    """Represents a chunk extracted from a single document page."""
    page_number: int
    chunk_index: int
    content: str
    token_count: int


class ChunkingService:
    """Sliding-window text chunker enforcing strict page boundaries and provenance."""

    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 100

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimates token count using standard ~4 chars per token heuristic."""
        if not text:
            return 0
        words = text.split()
        # Combination of word count and character estimation
        return max(len(words), len(text) // 4)

    @classmethod
    def chunk_page_text(
        cls,
        text: str,
        page_number: int,
        start_chunk_index: int = 0,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[ChunkItem]:
        """
        Splits a single page's text into overlapping chunks.
        Guarantees that chunks never span across page boundaries.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        chunks: List[ChunkItem] = []
        text_length = len(clean_text)

        # If text is smaller than chunk size, return it as a single chunk
        if text_length <= chunk_size:
            return [
                ChunkItem(
                    page_number=page_number,
                    chunk_index=start_chunk_index,
                    content=clean_text,
                    token_count=cls.estimate_tokens(clean_text),
                )
            ]

        step = max(1, chunk_size - chunk_overlap)
        current_start = 0
        current_index = start_chunk_index

        while current_start < text_length:
            current_end = min(text_length, current_start + chunk_size)
            chunk_content = clean_text[current_start:current_end]

            # Try to snap to natural word boundaries if not at the very end of text
            if current_end < text_length:
                last_space = chunk_content.rfind(" ")
                # Only snap if the space is in the latter half of the chunk
                if last_space > chunk_size // 2:
                    chunk_content = chunk_content[:last_space]
                    current_end = current_start + last_space

            stripped_content = chunk_content.strip()
            if stripped_content:
                chunks.append(
                    ChunkItem(
                        page_number=page_number,
                        chunk_index=current_index,
                        content=stripped_content,
                        token_count=cls.estimate_tokens(stripped_content),
                    )
                )
                current_index += 1

            if current_end >= text_length:
                break

            current_start = current_start + step

        return chunks

    @classmethod
    def chunk_document_pages(
        cls,
        pages: List[tuple[int, str]],  # List of (page_number, page_text)
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[ChunkItem]:
        """
        Iterates over all extracted pages of a document and chunks each page independently.
        Provenance is preserved: page_number is always physical and chunk_index is sequential.
        """
        all_chunks: List[ChunkItem] = []
        global_chunk_index = 0

        for page_number, page_text in pages:
            page_chunks = cls.chunk_page_text(
                text=page_text,
                page_number=page_number,
                start_chunk_index=global_chunk_index,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            all_chunks.extend(page_chunks)
            global_chunk_index += len(page_chunks)

        logger.debug(
            f"Chunked {len(pages)} pages into {len(all_chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})."
        )
        return all_chunks
