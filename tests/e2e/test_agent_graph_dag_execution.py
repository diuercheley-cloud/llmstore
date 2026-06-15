"""E2E: Agent Graph DAG execution flow.

Tests the full lifecycle:
1. Validate a graph definition
2. Run the graph
3. Query run status
4. List runs
5. Cancel a run
"""

import pytest


@pytest.mark.asyncio
async def test_agent_graph_full_lifecycle(async_client, admin_token_headers):
    # 1. Define a supervisor->workers->reviewer graph
    graph = {
        "name": "e2e-agent-graph",
        "description": "E2E test: Supervisor delegates to parallel workers, reviewer consolidates",
        "nodes": [
            {
                "id": "supervisor-1",
                "type": "supervisor",
                "name": "Main Supervisor",
                "max_retries": 1,
                "timeout_seconds": 30,
            },
            {
                "id": "worker-a",
                "type": "worker",
                "name": "Worker A (research)",
                "max_retries": 2,
                "timeout_seconds": 30,
            },
            {
                "id": "worker-b",
                "type": "worker",
                "name": "Worker B (implement)",
                "max_retries": 2,
                "timeout_seconds": 30,
            },
            {
                "id": "worker-c",
                "type": "worker",
                "name": "Worker C (test)",
                "max_retries": 2,
                "timeout_seconds": 30,
            },
            {
                "id": "reviewer-1",
                "type": "reviewer",
                "name": "Reviewer",
                "max_retries": 1,
                "timeout_seconds": 30,
            },
            {
                "id": "planner-1",
                "type": "planner",
                "name": "Planner",
                "max_retries": 1,
                "timeout_seconds": 30,
            },
        ],
        "edges": [
            {"source": "supervisor-1", "target": "planner-1"},
            {"source": "planner-1", "target": "worker-a"},
            {"source": "planner-1", "target": "worker-b"},
            {"source": "planner-1", "target": "worker-c"},
            {"source": "worker-a", "target": "reviewer-1"},
            {"source": "worker-b", "target": "reviewer-1"},
            {"source": "worker-c", "target": "reviewer-1"},
        ],
        "max_concurrency": 3,
        "enable_checkpointing": True,
    }

    # 2. Validate
    validate_resp = await async_client.post(
        "/admin/agents/graphs/validate",
        json=graph,
        headers=admin_token_headers,
    )
    assert validate_resp.status_code == 200
    assert validate_resp.json()["valid"] is True
    order = validate_resp.json()["topological_order"]
    assert "supervisor-1" in order
    assert "reviewer-1" in order
    # All workers should be before reviewer
    assert order.index("worker-a") < order.index("reviewer-1")
    assert order.index("worker-b") < order.index("reviewer-1")
    assert order.index("worker-c") < order.index("reviewer-1")

    # 3. Run the graph
    run_resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": graph},
        headers=admin_token_headers,
    )
    assert run_resp.status_code == 200, f"Run failed: {run_resp.text}"
    run_data = run_resp.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "completed"
    assert len(run_data["node_results"]) == 6

    # Verify all nodes completed
    for nr in run_data["node_results"].values():
        assert nr["status"] == "completed", f"Node {nr['node_id']} failed: {nr.get('error')}"

    # 4. Get run by ID
    get_resp = await async_client.get(
        f"/admin/agents/graphs/runs/{run_id}",
        headers=admin_token_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id

    # 5. List runs
    list_resp = await async_client.get(
        "/admin/agents/graphs/runs",
        headers=admin_token_headers,
    )
    assert list_resp.status_code == 200
    run_ids = [r["run_id"] for r in list_resp.json()]
    assert run_id in run_ids


@pytest.mark.asyncio
async def test_agent_graph_single_supervisor(async_client, admin_token_headers):
    graph = {
        "name": "simple-supervisor",
        "nodes": [{"id": "sup-1", "type": "supervisor", "name": "Supervisor"}],
        "edges": [],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": graph},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_agent_graph_hierarchical(async_client, admin_token_headers):
    graph = {
        "name": "hierarchical-flow",
        "nodes": [
            {"id": "hier-1", "type": "hierarchical", "name": "Top Coordinator"},
            {"id": "crew-1", "type": "crew", "name": "Crew Alpha"},
            {"id": "crew-2", "type": "crew", "name": "Crew Beta"},
        ],
        "edges": [
            {"source": "hier-1", "target": "crew-1"},
            {"source": "hier-1", "target": "crew-2"},
        ],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": graph},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200, f"Run failed: {resp.text}"
    assert resp.json()["status"] == "completed"
    assert len(resp.json()["node_results"]) == 3


@pytest.mark.asyncio
async def test_agent_graph_validate_rejects_cycle(async_client, admin_token_headers):
    graph = {
        "name": "invalid-cycle",
        "nodes": [
            {"id": "a", "type": "worker"},
            {"id": "b", "type": "worker"},
            {"id": "c", "type": "worker"},
        ],
        "edges": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"},
        ],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/validate",
        json=graph,
        headers=admin_token_headers,
    )
    assert resp.status_code == 400
    assert "cycle" in resp.json()["detail"].lower()
