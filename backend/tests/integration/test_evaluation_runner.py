"""Integration tests for Evaluation Runner and Quantitative Metrics."""

import pytest
from httpx import AsyncClient
from app.models.workspace import Workspace
from app.models.evaluation import EvaluationRun
from app.services.evaluation_service import EvaluationService


@pytest.mark.asyncio
async def test_evaluation_runner_full_suite(async_client: AsyncClient):
    """
    Test the quantitative evaluation runner on a fresh workspace.
    Verifies that:
      - Benchmark documents are automatically ingested.
      - Retrieval hit rate >= 85%.
      - Citation validity rate == 100%.
      - Negative abstention accuracy == 100%.
      - Results are persisted to database and accessible via API.
    """
    # 1. Create a test workspace
    ws_res = await async_client.post(
        "/api/v1/workspaces",
        json={"title": "Evaluation Benchmark Workspace", "description": "Automated evaluation testing."},
    )
    assert ws_res.status_code == 201
    workspace_id = ws_res.json()["id"]

    # 2. Trigger Evaluation Run via API
    eval_res = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/evaluations/run",
        json={"suite_name": "ProofLens Benchmark Suite v1"},
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()

    # 3. Assert Metric Thresholds
    assert eval_data["total_cases"] == 8
    assert eval_data["retrieval_hit_rate"] >= 0.85, f"Retrieval hit rate {eval_data['retrieval_hit_rate']} < 0.85"
    assert eval_data["citation_validity_rate"] == 1.0, f"Citation validity rate {eval_data['citation_validity_rate']} != 1.0"
    assert eval_data["abstention_accuracy"] == 1.0, f"Abstention accuracy {eval_data['abstention_accuracy']} != 1.0"
    assert eval_data["passed_cases"] >= 7

    eval_run_id = eval_data["id"]

    # 4. List evaluations
    list_res = await async_client.get(f"/api/v1/workspaces/{workspace_id}/evaluations")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert len(runs) >= 1
    assert any(r["id"] == eval_run_id for r in runs)

    # 5. Fetch single evaluation run
    get_res = await async_client.get(f"/api/v1/workspaces/{workspace_id}/evaluations/{eval_run_id}")
    assert get_res.status_code == 200
    single_run = get_res.json()
    assert single_run["id"] == eval_run_id
    assert "cases" in single_run["raw_results"]

    # 6. Cleanup workspace (cascade deletes evaluations)
    del_res = await async_client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert del_res.status_code == 204
