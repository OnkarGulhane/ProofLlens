"""Cross-Document Comparison Engine analyzing topic alignment across multiple documents."""

import json
import time
import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import logger
from app.core.exceptions import (
    WorkspaceNotFoundError,
    DocumentValidationError,
    DocumentNotFoundError,
)
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.comparison import ComparisonRun
from app.schemas.comparison import (
    ConsensusStatus,
    DocumentFinding,
    ComparisonSynthesis,
    ComparisonResponse,
)
from app.schemas.query import CitationDTO
from app.services.retrieval_service import RetrievalService, RetrievedChunk
from app.services.citation_service import CitationService
from app.services.qa_service import get_llm_provider, LLMProvider


class ComparisonService:
    """Orchestrates partitioned multi-document retrieval, comparative synthesis, and citation validation."""

    SYSTEM_PROMPT = (
        "You are ProofLens AI, an expert cross-document intelligence analyst.\n"
        "Your task is to compare what multiple documents state regarding a specific topic.\n\n"
        "RULES:\n"
        "1. For each document, summarize its factual claims using strict citations: [Doc: <doc_name>, Page: <page_num>].\n"
        "2. Classify the overall consensus as one of: AGREEMENT, DIFFERENCE, CONTRADICTION, or INCOMPARABLE.\n"
        "3. Provide an analytical synthesis explaining how the sources compare.\n"
        "4. If a document does not discuss the topic, state that clearly.\n"
        "5. Output valid JSON matching this schema:\n"
        "{\n"
        "  \"findings\": [{\"document_name\": \"...\", \"summary\": \"...\"}],\n"
        "  \"consensus\": \"AGREEMENT|DIFFERENCE|CONTRADICTION|INCOMPARABLE\",\n"
        "  \"analysis\": \"...\"\n"
        "}"
    )

    @classmethod
    async def compare_documents(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        topic: str,
        document_ids: List[uuid.UUID],
        llm_provider: Optional[LLMProvider] = None,
    ) -> ComparisonResponse:
        """Executes partitioned retrieval across selected documents and synthesizes a comparative matrix."""
        start_time = time.perf_counter()

        # 1. Validation checks
        if len(document_ids) < 2:
            raise DocumentValidationError("Cross-document comparison requires selecting at least two documents.")

        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await session.execute(ws_stmt)
        if not ws_res.scalar_one_or_none():
            raise WorkspaceNotFoundError(str(workspace_id))

        # Retrieve Document records to verify existence and get filenames
        docs_stmt = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.id.in_(document_ids),
        )
        docs_res = await session.execute(docs_stmt)
        docs_map = {doc.id: doc for doc in docs_res.scalars().all()}

        for doc_id in document_ids:
            if doc_id not in docs_map:
                raise DocumentNotFoundError(f"Document {doc_id} not found in workspace {workspace_id}")

        # 2. Partitioned Evidence Retrieval (per document)
        per_doc_chunks: Dict[uuid.UUID, List[RetrievedChunk]] = {}
        all_retrieved_chunks: List[RetrievedChunk] = []

        for doc_id in document_ids:
            chunks = await RetrievalService.retrieve_chunks(
                session=session,
                workspace_id=workspace_id,
                query=topic,
                document_ids=[doc_id],
                similarity_threshold=0.35,  # Lower threshold for comparative discovery
                top_k=3,
            )
            per_doc_chunks[doc_id] = chunks
            all_retrieved_chunks.extend(chunks)

        # 3. Assemble partitioned context prompt
        context_blocks = []
        for doc_id, doc in docs_map.items():
            chunks = per_doc_chunks.get(doc_id, [])
            block_header = f"=== Document: {doc.filename} (ID: {doc.id}) ==="
            if chunks:
                chunk_texts = [f"[Doc: {c.document_name}, Page: {c.page_number}]\n{c.content}" for c in chunks]
                block_content = "\n\n".join(chunk_texts)
            else:
                block_content = "No relevant passages found for this topic."
            context_blocks.append(f"{block_header}\n{block_content}")

        user_prompt = (
            f"Topic to Compare: {topic}\n\n"
            f"--- PARTITIONED DOCUMENT EVIDENCE ---\n"
            f"{chr(10).join(context_blocks)}\n"
            f"---------------------------------------\n\n"
            f"Generate a side-by-side comparison in the requested JSON format."
        )

        # 4. Generate comparison synthesis via LLM
        provider = llm_provider or get_llm_provider()
        raw_response = await provider.generate_response(cls.SYSTEM_PROMPT, user_prompt)

        # 5. Parse LLM response JSON or fallback synthesis
        parsed_findings: List[DocumentFinding] = []
        consensus: ConsensusStatus = ConsensusStatus.DIFFERENCE
        analysis: str = "Comparison generated based on retrieved passages."

        try:
            # Look for JSON payload in response
            json_start = raw_response.find("{")
            json_end = raw_response.rfind("}")
            if json_start != -1 and json_end != -1:
                json_str = raw_response[json_start : json_end + 1]
                data = json.loads(json_str)

                consensus_str = data.get("consensus", "DIFFERENCE").upper()
                if consensus_str in ConsensusStatus.__members__:
                    consensus = ConsensusStatus(consensus_str)
                analysis = data.get("analysis", analysis)

                for item in data.get("findings", []):
                    item_doc_name = item.get("document_name", "")
                    # Match to document record
                    target_doc = next(
                        (d for d in docs_map.values() if d.filename.lower() in item_doc_name.lower() or item_doc_name.lower() in d.filename.lower()),
                        None,
                    )
                    if target_doc:
                        summary_text = item.get("summary", "")
                        # Validate citations for this finding
                        parsed_cites = CitationService.parse_citations(summary_text)
                        verified_cites, unverified = CitationService.validate_citations(
                            parsed_cites, per_doc_chunks.get(target_doc.id, [])
                        )
                        clean_summary = CitationService.sanitize_answer_text(summary_text, unverified)

                        citation_dtos = [
                            CitationDTO(
                                citation_id=vc.citation_id,
                                chunk_id=vc.chunk_id,
                                document_id=vc.document_id,
                                document_name=vc.document_name,
                                page_number=vc.page_number,
                                cited_excerpt=vc.cited_excerpt,
                                verification_status=vc.verification_status,
                            )
                            for vc in verified_cites
                        ]

                        parsed_findings.append(
                            DocumentFinding(
                                document_id=target_doc.id,
                                document_name=target_doc.filename,
                                summary=clean_summary,
                                citations=citation_dtos,
                            )
                        )
        except Exception as parse_err:
            logger.warning(f"Could not parse LLM JSON response: {parse_err}. Using deterministic synthesis.")

        # Fallback if JSON parsing did not cover all documents
        if len(parsed_findings) < len(docs_map):
            parsed_findings = []
            has_conflicts = False

            for doc_id, doc in docs_map.items():
                chunks = per_doc_chunks.get(doc_id, [])
                if chunks:
                    top_chunk = chunks[0]
                    summary_text = f"According to {doc.filename}, {top_chunk.content[:150]} [Doc: {doc.filename}, Page: {top_chunk.page_number}]."
                    parsed_cites = CitationService.parse_citations(summary_text)
                    verified_cites, _ = CitationService.validate_citations(parsed_cites, chunks)

                    citation_dtos = [
                        CitationDTO(
                            citation_id=vc.citation_id,
                            chunk_id=vc.chunk_id,
                            document_id=vc.document_id,
                            document_name=vc.document_name,
                            page_number=vc.page_number,
                            cited_excerpt=vc.cited_excerpt,
                            verification_status=vc.verification_status,
                        )
                        for vc in verified_cites
                    ]
                else:
                    summary_text = f"No relevant passages concerning '{topic}' were found in {doc.filename}."
                    citation_dtos = []
                    has_conflicts = True

                parsed_findings.append(
                    DocumentFinding(
                        document_id=doc.id,
                        document_name=doc.filename,
                        summary=summary_text,
                        citations=citation_dtos,
                    )
                )

            consensus = ConsensusStatus.INCOMPARABLE if has_conflicts else ConsensusStatus.DIFFERENCE
            analysis = (
                f"Comparative analysis across {len(docs_map)} documents reveals distinct perspectives "
                f"or scope variations on '{topic}'."
            )

        # 6. Database Persistence
        comparison_run_id = uuid.uuid4()
        synthesis_obj = ComparisonSynthesis(consensus=consensus, analysis=analysis)

        matrix_data = {
            "findings": [f.model_dump(mode="json") for f in parsed_findings],
            "synthesis": synthesis_obj.model_dump(mode="json"),
        }

        comparison_run = ComparisonRun(
            id=comparison_run_id,
            workspace_id=workspace_id,
            topic=topic,
            document_ids=[str(d) for d in document_ids],
            comparison_matrix=matrix_data,
        )
        session.add(comparison_run)
        await session.commit()

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Completed cross-document comparison for topic '{topic[:30]}' across {len(document_ids)} docs in {elapsed_ms:.2f}ms."
        )

        return ComparisonResponse(
            comparison_run_id=comparison_run_id,
            workspace_id=workspace_id,
            topic=topic,
            documents_analyzed=document_ids,
            findings=parsed_findings,
            synthesis=synthesis_obj,
        )
