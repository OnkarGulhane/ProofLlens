"""Grounded Question Answering Service with citation validation and abstention policy."""

import abc
import time
import uuid
from typing import List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import WorkspaceNotFoundError
from app.models.workspace import Workspace
from app.models.query import QueryRun, Answer, RetrievedEvidence, Citation
from app.schemas.query import QueryResponse, CitationDTO
from app.schemas.retrieval import RetrievedChunkResponse
from app.services.retrieval_service import RetrievalService, RetrievedChunk
from app.services.citation_service import CitationService, VerifiedCitation


ABSTENTION_MESSAGE = "The available documents do not contain sufficient evidence to answer this question."


class LLMProvider(abc.ABC):
    """Abstract interface for generative LLM text completion."""

    @abc.abstractmethod
    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generates grounded text completion."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM generating grounded answers with citations based on retrieved chunks.
    Enables reproducible offline testing without external API dependencies.
    """

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        # Check if context contains chunks
        if "--- RETRIEVED CONTEXT ---" not in user_prompt:
            return ABSTENTION_MESSAGE

        # If user prompt has retrieved chunks, synthesize an answer with citations
        import re
        chunk_headers = re.findall(r"\[Doc:\s*([^,\]]+),\s*Page:\s*(\d+)\]", user_prompt)
        if not chunk_headers:
            return ABSTENTION_MESSAGE

        # Extract content snippet from the prompt
        doc_name, page_num = chunk_headers[0]
        # Look for sentence in context
        return (
            f"Based on the provided documents, {doc_name} indicates relevant findings on this topic "
            f"[Doc: {doc_name}, Page: {page_num}]."
        )


class OpenAILLMProvider(LLMProvider):
    """OpenAI GPT-4o-mini generative completion client."""

    def __init__(self):
        self._api_key = settings.OPENAI_API_KEY
        self._model = settings.OPENAI_MODEL
        self._client = httpx.AsyncClient(timeout=45.0)

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,  # Zero temperature for deterministic grounded answers
        }
        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class GeminiLLMProvider(LLMProvider):
    """Google Gemini generative completion client (e.g. gemini-1.5-flash)."""

    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY
        self._model = settings.GEMINI_MODEL
        self._client = httpx.AsyncClient(timeout=45.0)

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.0,
            },
        }
        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ABSTENTION_MESSAGE
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ABSTENTION_MESSAGE
        return parts[0].get("text", "").strip()


def get_llm_provider() -> LLMProvider:
    """Factory function providing the configured LLM provider."""
    if settings.GEMINI_API_KEY and (settings.LLM_PROVIDER.lower() == "gemini" or not settings.OPENAI_API_KEY):
        logger.info(f"Using GeminiLLMProvider ({settings.GEMINI_MODEL})")
        return GeminiLLMProvider()

    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        logger.info(f"Using OpenAILLMProvider ({settings.OPENAI_MODEL})")
        return OpenAILLMProvider()

    logger.info("No external LLM keys configured; using MockLLMProvider for offline execution.")
    return MockLLMProvider()


class QAService:
    """Orchestrates evidence retrieval, prompt grounding, citation validation, and persistence."""

    SYSTEM_PROMPT = (
        "You are ProofLens AI, an evidence-grounded document analysis engine.\n"
        "Answer the user's question ONLY using the factual statements in the provided Retrieved Context below.\n\n"
        "RULES:\n"
        "1. Every factual statement in your answer MUST cite its source using this format: [Doc: <doc_name>, Page: <page_num>].\n"
        "2. NEVER use prior knowledge, external assumptions, or invent facts.\n"
        "3. If the Retrieved Context does not explicitly contain enough information to answer the question, state exactly:\n"
        f"   \"{ABSTENTION_MESSAGE}\"\n"
        "4. Do NOT speculate, extrapolate, or invent document titles or page numbers."
    )

    @classmethod
    def format_user_prompt(cls, question: str, chunks: List[RetrievedChunk]) -> str:
        """Assembles prompt with strict context boundaries."""
        context_blocks = []
        for c in chunks:
            context_blocks.append(
                f"[Doc: {c.document_name}, Page: {c.page_number}]\n{c.content}"
            )
        joined_context = "\n\n".join(context_blocks)
        return (
            f"Question: {question}\n\n"
            f"--- RETRIEVED CONTEXT ---\n"
            f"{joined_context}\n"
            f"-------------------------\n\n"
            f"Provide an evidence-grounded answer citing the exact document and page."
        )

    @classmethod
    async def answer_question(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        question: str,
        document_ids: Optional[List[uuid.UUID]] = None,
        similarity_threshold: float = 0.65,
        top_k: int = 5,
        llm_provider: Optional[LLMProvider] = None,
    ) -> QueryResponse:
        """Executes the full grounded question answering pipeline with citation validation."""
        start_time = time.perf_counter()

        # 1. Verify workspace exists
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await session.execute(ws_stmt)
        if not ws_res.scalar_one_or_none():
            raise WorkspaceNotFoundError(str(workspace_id))

        # 2. Retrieve evidence chunks
        retrieved_chunks = await RetrievalService.retrieve_chunks(
            session=session,
            workspace_id=workspace_id,
            query=question,
            document_ids=document_ids,
            similarity_threshold=similarity_threshold,
            top_k=top_k,
        )

        query_run_id = uuid.uuid4()
        answer_id = uuid.uuid4()

        # 3. Pre-generation Abstention Check: If 0 chunks exceed threshold, abstain immediately!
        if len(retrieved_chunks) == 0:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            reason = f"No retrieved passages met the minimum relevance threshold of {similarity_threshold}."

            query_run = QueryRun(
                id=query_run_id,
                workspace_id=workspace_id,
                question=question,
                selected_document_ids=[str(d) for d in document_ids] if document_ids else None,
                similarity_threshold=similarity_threshold,
                top_k=top_k,
                execution_time_ms=elapsed_ms,
            )
            session.add(query_run)

            answer_record = Answer(
                id=answer_id,
                query_run_id=query_run_id,
                answer_text=ABSTENTION_MESSAGE,
                status="ABSTAINED",
                is_abstained=True,
                abstention_reason=reason,
            )
            session.add(answer_record)
            await session.commit()

            return QueryResponse(
                query_run_id=query_run_id,
                workspace_id=workspace_id,
                question=question,
                answer=ABSTENTION_MESSAGE,
                is_abstained=True,
                abstention_reason=reason,
                citations=[],
                retrieved_evidence=[],
            )

        # 4. Generate answer via LLM
        provider = llm_provider or get_llm_provider()
        user_prompt = cls.format_user_prompt(question, retrieved_chunks)
        raw_answer = await provider.generate_response(cls.SYSTEM_PROMPT, user_prompt)

        # 5. Server-Side Citation Validation Pipeline
        parsed_cites = CitationService.parse_citations(raw_answer)
        verified_cites, unverified_cites = CitationService.validate_citations(parsed_cites, retrieved_chunks)
        clean_answer = CitationService.sanitize_answer_text(raw_answer, unverified_cites)

        # 6. Post-generation Abstention Policy Check
        is_abstained = False
        abstention_reason: Optional[str] = None

        if ABSTENTION_MESSAGE.lower() in clean_answer.lower():
            is_abstained = True
            abstention_reason = "Retrieved evidence does not contain sufficient facts to answer the question."
        elif len(parsed_cites) > 0 and len(verified_cites) == 0:
            # All claimed citations were hallucinated/unverified
            is_abstained = True
            clean_answer = ABSTENTION_MESSAGE
            abstention_reason = "Generated citations could not be verified against source evidence."

        # 7. Persist QueryRun, Answer, RetrievedEvidence, and Citations
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        query_run = QueryRun(
            id=query_run_id,
            workspace_id=workspace_id,
            question=question,
            selected_document_ids=[str(d) for d in document_ids] if document_ids else None,
            similarity_threshold=similarity_threshold,
            top_k=top_k,
            execution_time_ms=elapsed_ms,
        )
        session.add(query_run)

        answer_record = Answer(
            id=answer_id,
            query_run_id=query_run_id,
            answer_text=clean_answer,
            status="ABSTAINED" if is_abstained else "SUCCESS",
            is_abstained=is_abstained,
            abstention_reason=abstention_reason,
        )
        session.add(answer_record)

        # Persist retrieved evidences
        for c in retrieved_chunks:
            session.add(
                RetrievedEvidence(
                    id=uuid.uuid4(),
                    query_run_id=query_run_id,
                    chunk_id=c.chunk_id,
                    similarity_score=c.similarity_score,
                    rank=c.rank,
                )
            )

        # Persist verified citations if not abstained
        citation_dtos: List[CitationDTO] = []
        if not is_abstained:
            for vc in verified_cites:
                session.add(
                    Citation(
                        id=vc.citation_id,
                        answer_id=answer_id,
                        chunk_id=vc.chunk_id,
                        document_id=vc.document_id,
                        page_number=vc.page_number,
                        cited_excerpt=vc.cited_excerpt,
                        verification_status=vc.verification_status,
                    )
                )
                citation_dtos.append(
                    CitationDTO(
                        citation_id=vc.citation_id,
                        chunk_id=vc.chunk_id,
                        document_id=vc.document_id,
                        document_name=vc.document_name,
                        page_number=vc.page_number,
                        cited_excerpt=vc.cited_excerpt,
                        verification_status=vc.verification_status,
                    )
                )

        await session.commit()

        evidence_responses = [
            RetrievedChunkResponse(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                content=c.content,
                similarity_score=c.similarity_score,
                rank=c.rank,
            )
            for c in retrieved_chunks
        ]

        logger.info(
            f"Completed Q&A query '{question[:40]}...' in {elapsed_ms}ms "
            f"(abstained={is_abstained}, citations={len(citation_dtos)})."
        )

        return QueryResponse(
            query_run_id=query_run_id,
            workspace_id=workspace_id,
            question=question,
            answer=clean_answer,
            is_abstained=is_abstained,
            abstention_reason=abstention_reason,
            citations=citation_dtos,
            retrieved_evidence=evidence_responses,
        )
