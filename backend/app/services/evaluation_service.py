"""Evaluation Service for executing benchmark suites and scoring quantitative metrics."""

import io
import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject

from app.core.logging import logger
from app.core.exceptions import WorkspaceNotFoundError
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.evaluation import EvaluationRun
from app.schemas.evaluation import EvaluationRunResponse, EvaluationCaseResult
from app.services.document_service import DocumentService
from app.services.retrieval_service import RetrievalService
from app.services.qa_service import QAService, MockLLMProvider


DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "tests",
    "fixtures",
    "eval_dataset_v1.json",
)


def generate_benchmark_pdf(pages_text: List[str]) -> bytes:
    """Generates a valid standard PDF binary containing the specified page texts."""
    writer = PdfWriter()
    for text in pages_text:
        page = writer.add_blank_page(width=400, height=400)
        escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        text_stream = f"BT /F1 12 Tf 50 250 Td ({escaped_text}) Tj ET".encode("latin1")
        stream = DecodedStreamObject()
        stream.set_data(text_stream)
        page[NameObject("/Contents")] = stream

        font = DictionaryObject()
        font[NameObject("/Type")] = NameObject("/Font")
        font[NameObject("/Subtype")] = NameObject("/Type1")
        font[NameObject("/BaseFont")] = NameObject("/Helvetica")

        res = DictionaryObject()
        res[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
        page[NameObject("/Resources")] = res

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class EvaluationService:
    """Service for running standardized benchmark test suites on workspaces."""

    @classmethod
    def load_dataset(cls, dataset_path: Optional[str] = None) -> Dict[str, Any]:
        """Loads benchmark dataset from JSON file."""
        path = dataset_path or DEFAULT_DATASET_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Benchmark dataset fixture not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    async def ensure_benchmark_documents(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        dataset: Dict[str, Any],
    ) -> List[Document]:
        """Ensures that all benchmark documents required by the dataset exist in the workspace."""
        existing_docs_stmt = select(Document).where(Document.workspace_id == workspace_id)
        res = await session.execute(existing_docs_stmt)
        existing_docs = {d.filename: d for d in res.scalars().all()}

        ready_docs: List[Document] = []
        for doc_def in dataset.get("documents", []):
            filename = doc_def["filename"]
            pages = doc_def.get("pages", [])

            if filename in existing_docs:
                ready_docs.append(existing_docs[filename])
                continue

            # Ingest missing benchmark document
            logger.info(f"Ingesting missing benchmark document '{filename}' into workspace {workspace_id}")
            pdf_bytes = generate_benchmark_pdf(pages)
            doc = await DocumentService.process_and_store_document(
                session=session,
                workspace_id=workspace_id,
                filename=filename,
                content=pdf_bytes,
            )
            ready_docs.append(doc)

        return ready_docs

    @classmethod
    async def run_evaluation_suite(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        dataset_path: Optional[str] = None,
        custom_dataset: Optional[Dict[str, Any]] = None,
    ) -> EvaluationRun:
        """
        Executes the benchmark evaluation suite against the specified workspace.
        Calculates:
          - Retrieval Hit Rate (Target: >= 85%)
          - Citation Validity Rate (Target: 100%)
          - Negative Abstention Accuracy (Target: 100%)
        Persists EvaluationRun in database and returns the record.
        """
        # 1. Verify workspace exists
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await session.execute(ws_stmt)
        workspace = ws_res.scalar_one_or_none()
        if not workspace:
            raise WorkspaceNotFoundError(str(workspace_id))

        # 2. Load dataset and ensure documents are ingested
        dataset = custom_dataset or cls.load_dataset(dataset_path)
        suite_name = dataset.get("suite_name", "ProofLens Benchmark Suite")
        await cls.ensure_benchmark_documents(session, workspace_id, dataset)

        test_cases = dataset.get("test_cases", [])
        total_cases = len(test_cases)
        case_results: List[Dict[str, Any]] = []

        total_positive_cases = 0
        retrieval_hits = 0

        total_citations = 0
        valid_citations = 0

        total_negative_cases = 0
        correct_abstentions = 0

        passed_cases = 0

        mock_llm = MockLLMProvider()

        # 3. Iterate through benchmark cases
        for case in test_cases:
            case_id = case["id"]
            case_type = case["type"]
            query = case["query"]
            exp_filename = case.get("expected_document_filename")
            exp_page = case.get("expected_page_number")
            exp_abstain = case.get("expected_abstain", False)

            t0 = time.perf_counter()

            # Retrieval Probe
            retrieval_hit: Optional[bool] = None
            if exp_filename and exp_page:
                total_positive_cases += 1
                retrieved_chunks = await RetrievalService.retrieve_chunks(
                    session=session,
                    workspace_id=workspace_id,
                    query=query,
                    similarity_threshold=0.40,
                    top_k=5,
                )
                hit = any(
                    (c.document_name == exp_filename and c.page_number == exp_page)
                    for c in retrieved_chunks
                )
                if hit:
                    retrieval_hits += 1
                    retrieval_hit = True
                else:
                    retrieval_hit = False

            # End-to-End Q&A Execution
            qa_res = await QAService.answer_question(
                session=session,
                workspace_id=workspace_id,
                question=query,
                similarity_threshold=0.40,
                top_k=5,
                llm_provider=mock_llm,
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            # Citation Accounting
            for cite in qa_res.citations:
                total_citations += 1
                if cite.verification_status == "VERIFIED":
                    valid_citations += 1

            # Determine PASS/FAIL by case type
            status = "FAIL"
            notes = ""

            if case_type == "POSITIVE":
                if not qa_res.is_abstained and (retrieval_hit is True or retrieval_hit is None):
                    status = "PASS"
                    notes = f"Answer grounded with {len(qa_res.citations)} verified citation(s)."
                else:
                    status = "FAIL"
                    notes = f"Abstained unexpectedly or retrieval miss (hit={retrieval_hit})."

            elif case_type in ("NEGATIVE", "INJECTION"):
                total_negative_cases += 1
                if qa_res.is_abstained == exp_abstain:
                    correct_abstentions += 1
                    status = "PASS"
                    notes = f"Successfully abstained with reason: {qa_res.abstention_reason}"
                else:
                    status = "FAIL"
                    notes = "Failed to abstain on unsupported query."

            if status == "PASS":
                passed_cases += 1

            case_results.append({
                "id": case_id,
                "type": case_type,
                "query": query,
                "status": status,
                "retrieval_hit": retrieval_hit,
                "is_abstained": qa_res.is_abstained,
                "citations_count": len(qa_res.citations),
                "latency_ms": latency_ms,
                "notes": notes,
            })

        # 4. Compute Aggregate Metrics
        retrieval_hit_rate = (
            round(retrieval_hits / total_positive_cases, 4) if total_positive_cases > 0 else 1.0
        )
        citation_validity_rate = (
            round(valid_citations / total_citations, 4) if total_citations > 0 else 1.0
        )
        abstention_accuracy = (
            round(correct_abstentions / total_negative_cases, 4) if total_negative_cases > 0 else 1.0
        )

        # 5. Persist EvaluationRun
        eval_run_id = uuid.uuid4()
        eval_record = EvaluationRun(
            id=eval_run_id,
            workspace_id=workspace_id,
            suite_name=suite_name,
            total_cases=total_cases,
            passed_cases=passed_cases,
            retrieval_hit_rate=retrieval_hit_rate,
            citation_validity_rate=citation_validity_rate,
            abstention_accuracy=abstention_accuracy,
            raw_results={
                "cases": case_results,
                "summary": {
                    "total_positive_cases": total_positive_cases,
                    "retrieval_hits": retrieval_hits,
                    "total_citations": total_citations,
                    "valid_citations": valid_citations,
                    "total_negative_cases": total_negative_cases,
                    "correct_abstentions": correct_abstentions,
                },
            },
        )
        session.add(eval_record)
        await session.commit()
        await session.refresh(eval_record)

        logger.info(
            f"EvaluationRun {eval_run_id} completed: "
            f"Pass={passed_cases}/{total_cases}, "
            f"RetrievalHitRate={retrieval_hit_rate:.1%}, "
            f"CitationValidity={citation_validity_rate:.1%}, "
            f"AbstentionAccuracy={abstention_accuracy:.1%}"
        )

        return eval_record


async def cli_main() -> None:
    """CLI runner for executing the evaluation suite from terminal."""
    import sys
    from app.core.database import AsyncSessionLocal, engine
    from app.models.workspace import Workspace

    print("=" * 65)
    print(" ProofLens AI — Quantitative Benchmark Evaluation Runner")
    print("=" * 65)

    async with AsyncSessionLocal() as session:
        # Check or create evaluation workspace
        ws_stmt = select(Workspace).order_by(Workspace.created_at.desc())
        res = await session.execute(ws_stmt)
        workspace = res.scalars().first()

        if not workspace:
            workspace = Workspace(
                id=uuid.uuid4(),
                title="ProofLens Benchmark Workspace",
                description="Workspace automatically initialized for quantitative evaluation.",
            )
            session.add(workspace)
            await session.commit()
            print(f"Created evaluation workspace: {workspace.id}")
        else:
            print(f"Using workspace: '{workspace.title}' ({workspace.id})")

        print("Running benchmark suite...")
        run = await EvaluationService.run_evaluation_suite(
            session=session,
            workspace_id=workspace.id,
        )

        print("\n" + "=" * 65)
        print(" BENCHMARK EVALUATION RESULTS")
        print("=" * 65)
        print(f" Suite:                 {run.suite_name}")
        print(f" Total Test Cases:      {run.total_cases}")
        print(f" Passed Test Cases:     {run.passed_cases}/{run.total_cases} ({run.passed_cases/run.total_cases:.1%})")
        print(f" Retrieval Hit Rate:    {run.retrieval_hit_rate:.1%} (Target >= 85%)")
        print(f" Citation Validity:     {run.citation_validity_rate:.1%} (Target 100%)")
        print(f" Abstention Accuracy:   {run.abstention_accuracy:.1%} (Target 100%)")
        print("-" * 65)
        print(f"{'ID':<12} | {'TYPE':<10} | {'STATUS':<6} | {'LATENCY':<8} | {'NOTES'}")
        print("-" * 65)
        for c in run.raw_results.get("cases", []):
            print(f"{c['id']:<12} | {c['type']:<10} | {c['status']:<6} | {c['latency_ms']:<6}ms | {c['notes'][:35]}")
        print("=" * 65)

    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(cli_main())

