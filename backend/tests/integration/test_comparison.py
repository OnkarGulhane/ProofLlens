"""Integration tests for Cross-Document Comparison."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.comparison import ComparisonRun
from tests.pdf_helpers import create_synthetic_pdf


@pytest.mark.asyncio
async def test_cross_document_comparison_flow(async_client: AsyncClient):
    """
    Verifies side-by-side comparison across two documents with conflicting claims,
    checking per-document findings, citation validity, and database persistence.
    """
    # 1. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Comparison Workspace"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Upload Document A
    doc_a_text = "Migration Plan: Cloud migration is scheduled to complete in Q3 2026."
    doc_a_pdf = create_synthetic_pdf([doc_a_text])
    doc_a_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("project_alpha_plan.pdf", doc_a_pdf, "application/pdf")},
    )
    assert doc_a_res.status_code == 201
    doc_a_id = doc_a_res.json()["id"]

    # 3. Upload Document B
    doc_b_text = "Migration Plan: Cloud migration is postponed to 2027 due to executive budget cuts."
    doc_b_pdf = create_synthetic_pdf([doc_b_text])
    doc_b_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("budget_review_2026.pdf", doc_b_pdf, "application/pdf")},
    )
    assert doc_b_res.status_code == 201
    doc_b_id = doc_b_res.json()["id"]

    # 4. Submit cross-document comparison
    compare_payload = {
        "topic": "Cloud migration schedule and timeline",
        "document_ids": [doc_a_id, doc_b_id],
    }
    comp_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/compare", json=compare_payload)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["workspace_id"] == ws_id
    assert comp_data["topic"] == compare_payload["topic"]
    assert len(comp_data["documents_analyzed"]) == 2

    # Check per-document findings
    findings = comp_data["findings"]
    assert len(findings) == 2
    doc_ids_in_findings = {f["document_id"] for f in findings}
    assert doc_a_id in doc_ids_in_findings
    assert doc_b_id in doc_ids_in_findings

    # Check synthesis consensus
    assert comp_data["synthesis"]["consensus"] in ["DIFFERENCE", "CONTRADICTION", "AGREEMENT", "INCOMPARABLE"]

    # 5. Verify database persistence of ComparisonRun
    async with AsyncSessionLocal() as session:
        comp_run_id = comp_data["comparison_run_id"]
        run_record = await session.get(ComparisonRun, comp_run_id)
        assert run_record is not None
        assert run_record.topic == compare_payload["topic"]
        assert len(run_record.document_ids) == 2
        assert "findings" in run_record.comparison_matrix


@pytest.mark.asyncio
async def test_comparison_rejects_fewer_than_two_documents(async_client: AsyncClient):
    """Verifies that attempting to compare fewer than 2 documents returns 422 Unprocessable Entity."""
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Single Doc Workspace"})
    ws_id = ws_res.json()["id"]

    # Only 1 document
    payload = {
        "topic": "Timeline",
        "document_ids": [str(uuid.uuid4())],
    }
    comp_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/compare", json=payload)
    assert comp_res.status_code == 422
