"""Integration tests for Semantic Retrieval, threshold filtering, and workspace scoping."""

import pytest
from httpx import AsyncClient
from tests.pdf_helpers import create_synthetic_pdf


@pytest.mark.asyncio
async def test_semantic_retrieval_and_filtering(async_client: AsyncClient):
    """
    Verifies semantic vector retrieval, relevance threshold filtering,
    document subset filtering, and strict workspace isolation.
    """
    # 1. Create Workspace 1
    ws1_res = await async_client.post("/api/v1/workspaces", json={"title": "Primary Retrieval Workspace"})
    assert ws1_res.status_code == 201
    ws1_id = ws1_res.json()["id"]

    # 2. Upload Document A (Financial Topic) to Workspace 1
    doc_a_text = "Financial Earnings: In the third quarter, net operating income reached fourteen million dollars."
    doc_a_pdf = create_synthetic_pdf([doc_a_text])
    doc_a_res = await async_client.post(
        f"/api/v1/workspaces/{ws1_id}/documents",
        files={"file": ("financial_earnings.pdf", doc_a_pdf, "application/pdf")},
    )
    assert doc_a_res.status_code == 201
    doc_a_id = doc_a_res.json()["id"]

    # 3. Upload Document B (Engineering Specs) to Workspace 1
    doc_b_text = "System Architecture: The microservices cluster communicates via high throughput gRPC pipelines."
    doc_b_pdf = create_synthetic_pdf([doc_b_text])
    doc_b_res = await async_client.post(
        f"/api/v1/workspaces/{ws1_id}/documents",
        files={"file": ("system_architecture.pdf", doc_b_pdf, "application/pdf")},
    )
    assert doc_b_res.status_code == 201
    doc_b_id = doc_b_res.json()["id"]

    # 4. Execute Retrieval Query for Document A topic
    query_payload = {
        "query": "Financial Earnings: In the third quarter, net operating income reached fourteen million dollars.",
        "similarity_threshold": 0.5,
        "top_k": 5,
    }
    ret_res = await async_client.post(f"/api/v1/workspaces/{ws1_id}/retrieve", json=query_payload)
    assert ret_res.status_code == 200
    ret_data = ret_res.json()
    assert ret_data["total_found"] > 0
    top_chunk = ret_data["retrieved_chunks"][0]
    assert top_chunk["document_id"] == doc_a_id
    assert "fourteen million" in top_chunk["content"]
    assert top_chunk["rank"] == 1

    # 5. Test Document Filter: restrict search exclusively to Document B
    filter_payload = {
        "query": "What is the architecture?",
        "document_ids": [doc_b_id],
        "similarity_threshold": 0.0,  # Allow any match to verify filter
        "top_k": 5,
    }
    filtered_res = await async_client.post(f"/api/v1/workspaces/{ws1_id}/retrieve", json=filter_payload)
    assert filtered_res.status_code == 200
    filtered_chunks = filtered_res.json()["retrieved_chunks"]
    # Every returned chunk MUST belong to Document B
    for chunk in filtered_chunks:
        assert chunk["document_id"] == doc_b_id
        assert chunk["document_id"] != doc_a_id

    # 6. Test High Threshold Filtering (zero candidates above threshold)
    strict_payload = {
        "query": "Unrelated topic about deep sea marine biology exploration.",
        "similarity_threshold": 0.999,  # Impossibly high threshold
        "top_k": 5,
    }
    strict_res = await async_client.post(f"/api/v1/workspaces/{ws1_id}/retrieve", json=strict_payload)
    assert strict_res.status_code == 200
    assert strict_res.json()["total_found"] == 0

    # 7. Test Workspace Isolation: create Workspace 2 and verify zero cross-workspace leakage
    ws2_res = await async_client.post("/api/v1/workspaces", json={"title": "Isolated Empty Workspace"})
    ws2_id = ws2_res.json()["id"]

    ws2_query = {
        "query": "Financial Earnings",
        "similarity_threshold": 0.0,
        "top_k": 5,
    }
    ws2_ret_res = await async_client.post(f"/api/v1/workspaces/{ws2_id}/retrieve", json=ws2_query)
    assert ws2_ret_res.status_code == 200
    # Workspace 2 has no documents, must return 0 chunks
    assert ws2_ret_res.json()["total_found"] == 0
