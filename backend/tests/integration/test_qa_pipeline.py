"""Integration tests for Grounded Question Answering and Citation Pipeline."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.query import QueryRun, Answer, Citation, RetrievedEvidence
from app.services.qa_service import ABSTENTION_MESSAGE
from tests.pdf_helpers import create_synthetic_pdf


@pytest.mark.asyncio
async def test_grounded_qa_pipeline_with_verified_citations(async_client: AsyncClient):
    """
    Verifies end-to-end grounded question answering:
    retrieves evidence, generates response, validates citations, and persists query run.
    """
    # 1. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Q&A Pipeline Workspace"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Upload document with known facts
    p1 = "Financial Q3 report: Total operating revenue reached fourteen million dollars."
    p2 = "Infrastructure note: Cloud server expenses remained stable at two million."
    pdf_bytes = create_synthetic_pdf([p1, p2])

    upload_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("q3_financials.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 3. Submit grounded question
    query_payload = {
        "question": "Financial Q3 report: Total operating revenue reached fourteen million dollars.",
        "similarity_threshold": 0.5,
        "top_k": 5,
    }
    qa_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/query", json=query_payload)
    assert qa_res.status_code == 200
    qa_data = qa_res.json()

    assert qa_data["is_abstained"] is False
    assert len(qa_data["citations"]) > 0
    top_citation = qa_data["citations"][0]
    assert top_citation["document_id"] == doc_id
    assert top_citation["page_number"] == 1
    assert top_citation["verification_status"] == "VERIFIED"
    assert len(qa_data["retrieved_evidence"]) > 0

    # 4. Verify database records
    async with AsyncSessionLocal() as session:
        query_run_id = qa_data["query_run_id"]
        # Check QueryRun
        qr = await session.get(QueryRun, query_run_id)
        assert qr is not None
        assert qr.question == query_payload["question"]

        # Check Answer
        ans_stmt = select(Answer).where(Answer.query_run_id == query_run_id)
        ans = (await session.execute(ans_stmt)).scalar_one_or_none()
        assert ans is not None
        assert ans.is_abstained is False

        # Check Citations
        cite_stmt = select(Citation).where(Citation.answer_id == ans.id)
        cites = list((await session.execute(cite_stmt)).scalars().all())
        assert len(cites) > 0
        assert cites[0].verification_status == "VERIFIED"


@pytest.mark.asyncio
async def test_qa_pipeline_insufficient_evidence_abstention(async_client: AsyncClient):
    """
    Verifies that asking a question absent from the corpus produces explicit abstention.
    """
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Abstention Workspace"})
    ws_id = ws_res.json()["id"]

    # Submit query with impossible threshold to simulate absent evidence
    query_payload = {
        "question": "What is the return policy for international orders?",
        "similarity_threshold": 0.999,
        "top_k": 5,
    }
    qa_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/query", json=query_payload)
    assert qa_res.status_code == 200
    qa_data = qa_res.json()

    assert qa_data["is_abstained"] is True
    assert ABSTENTION_MESSAGE in qa_data["answer"]
    assert len(qa_data["citations"]) == 0
    assert "No retrieved passages met" in qa_data["abstention_reason"]
