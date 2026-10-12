"""Integration tests for workspace creation and document ingestion flow."""

import os
import uuid
import pytest
from httpx import AsyncClient
from tests.pdf_helpers import create_synthetic_pdf


@pytest.mark.asyncio
async def test_full_document_ingestion_lifecycle(async_client: AsyncClient):
    """Verifies workspace creation, PDF upload, page extraction, listing, and deletion."""
    # 1. Create a new workspace
    ws_payload = {
        "title": "Ingestion Integration Workspace",
        "description": "Validating PDF parsing and storage",
    }
    ws_res = await async_client.post("/api/v1/workspaces", json=ws_payload)
    assert ws_res.status_code == 201
    workspace = ws_res.json()
    ws_id = workspace["id"]

    # 2. Upload a 2-page synthetic PDF
    p1 = "First page text of the technical specification document for ProofLens AI."
    p2 = "Second page text with operational parameters and security architecture."
    pdf_bytes = create_synthetic_pdf([p1, p2])

    files = {"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}
    upload_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/documents", files=files)
    assert upload_res.status_code == 201

    doc = upload_res.json()
    doc_id = doc["id"]
    assert doc["filename"] == "test_doc.pdf"
    assert doc["total_pages"] == 2
    assert doc["status"] == "READY"

    # 3. Test duplicate upload rejection in the same workspace
    dup_res = await async_client.post(f"/api/v1/workspaces/{ws_id}/documents", files={"file": ("test_doc.pdf", pdf_bytes, "application/pdf")})
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["message"]

    # 4. List documents in workspace
    list_res = await async_client.get(f"/api/v1/workspaces/{ws_id}/documents")
    assert list_res.status_code == 200
    docs_list = list_res.json()
    assert len(docs_list) == 1
    assert docs_list[0]["id"] == doc_id

    # 5. Get document details including extracted pages
    detail_res = await async_client.get(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["pages"]) == 2
    assert detail["pages"][0]["page_number"] == 1
    assert p1 in detail["pages"][0]["raw_text"]
    assert detail["pages"][1]["page_number"] == 2
    assert p2 in detail["pages"][1]["raw_text"]

    # 6. Delete document
    del_res = await async_client.delete(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}")
    assert del_res.status_code == 204

    # Verify document is gone
    get_res = await async_client.get(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_upload_non_pdf_rejection(async_client: AsyncClient):
    """Verifies that non-PDF files are rejected with 400 Bad Request."""
    ws_res = await async_client.post("/api/v1/workspaces", json={"title": "Rejection Workspace"})
    ws_id = ws_res.json()["id"]

    fake_file = {"file": ("malicious.txt", b"Random string not a PDF", "text/plain")}
    res = await async_client.post(f"/api/v1/workspaces/{ws_id}/documents", files=fake_file)
    assert res.status_code == 400
    assert "invalid magic bytes" in res.json()["message"].lower()
