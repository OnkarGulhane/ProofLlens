"""Server-Side Citation Validation Engine preventing AI hallucinations."""

import re
import uuid
from typing import List, Tuple, NamedTuple, Optional
from app.core.logging import logger
from app.services.retrieval_service import RetrievedChunk


class ParsedCitation(NamedTuple):
    """Raw citation parsed from LLM response text."""
    document_name: str
    page_number: int
    raw_marker: str


class VerifiedCitation(NamedTuple):
    """Citation verified against retrieved candidate chunks."""
    citation_id: uuid.UUID
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    cited_excerpt: str
    verification_status: str  # VERIFIED, UNVERIFIED


class CitationService:
    """Regex-based citation extraction and server-side verification against ground-truth chunks."""

    # Matches markers like: [Doc: annual_report.pdf, Page: 4] or [Document: report.pdf, Page: 12]
    CITATION_REGEX = re.compile(
        r"\[(?:Doc|Document):\s*([^,\]]+),\s*(?:Page|p\.?):\s*(\d+)\]",
        re.IGNORECASE,
    )

    @classmethod
    def parse_citations(cls, text: str) -> List[ParsedCitation]:
        """Extracts all bracketed document/page citations from the text."""
        matches = cls.CITATION_REGEX.finditer(text)
        citations: List[ParsedCitation] = []

        for match in matches:
            raw_marker = match.group(0)
            doc_name = match.group(1).strip()
            page_num = int(match.group(2))
            citations.append(
                ParsedCitation(
                    document_name=doc_name,
                    page_number=page_num,
                    raw_marker=raw_marker,
                )
            )

        return citations

    @classmethod
    def validate_citations(
        cls,
        parsed_citations: List[ParsedCitation],
        retrieved_chunks: List[RetrievedChunk],
    ) -> Tuple[List[VerifiedCitation], List[ParsedCitation]]:
        """
        Cross-references claimed citations against actual retrieved chunks.
        Returns:
            (verified_citations, unverified_citations)
        """
        verified: List[VerifiedCitation] = []
        unverified: List[ParsedCitation] = []

        for cite in parsed_citations:
            matched_chunk: Optional[RetrievedChunk] = None

            # Look for a retrieved chunk that matches document name and page number
            for chunk in retrieved_chunks:
                # Check filename match (case-insensitive, exact or substring)
                chunk_doc_name = chunk.document_name.lower().strip()
                claimed_doc_name = cite.document_name.lower().strip()

                name_matches = (
                    chunk_doc_name == claimed_doc_name
                    or claimed_doc_name in chunk_doc_name
                    or chunk_doc_name in claimed_doc_name
                )
                page_matches = chunk.page_number == cite.page_number

                if name_matches and page_matches:
                    matched_chunk = chunk
                    break

            if matched_chunk:
                # Excerpt up to first 250 characters of chunk content
                excerpt = matched_chunk.content[:250].strip() + ("..." if len(matched_chunk.content) > 250 else "")
                verified.append(
                    VerifiedCitation(
                        citation_id=uuid.uuid4(),
                        chunk_id=matched_chunk.chunk_id,
                        document_id=matched_chunk.document_id,
                        document_name=matched_chunk.document_name,
                        page_number=matched_chunk.page_number,
                        cited_excerpt=excerpt,
                        verification_status="VERIFIED",
                    )
                )
            else:
                logger.warning(
                    f"Hallucination detected: Citation [Doc: '{cite.document_name}', Page: {cite.page_number}] "
                    f"does not exist in the retrieved evidence set."
                )
                unverified.append(cite)

        return verified, unverified

    @classmethod
    def sanitize_answer_text(cls, text: str, unverified_citations: List[ParsedCitation]) -> str:
        """Removes unverified citation markers from the answer text."""
        sanitized = text
        for unverified in unverified_citations:
            sanitized = sanitized.replace(unverified.raw_marker, "")
        # Clean up any leftover double spaces
        return re.sub(r" +", " ", sanitized).strip()
