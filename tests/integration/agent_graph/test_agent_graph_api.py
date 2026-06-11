import pytest


@pytest.mark.asyncio
async def test_run_graph(async_client, admin_token_headers):
    payload = {
        "name": "integration-test-graph",
        "nodes": [
            {"id": "planner-1", "type": "planner", "name": "Planner"},
            {"id": "worker-1", "type": "worker", "name": "Worker 1"},
            {"id": "worker-2", "type": "worker", "name": "Worker 2"},
            {"id": "reviewer-1", "type": "reviewer", "name": "Reviewer"},
        ],
        "edges": [
            {"source": "planner-1", "target": "worker-1"},
            {"source": "planner-1", "target": "worker-2"},
            {"source": "worker-1", "target": "reviewer-1"},
            {"source": "worker-2", "target": "reviewer-1"},
        ],
        "max_concurrency": 4,
        "enable_checkpointing": True,
    }
    resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": payload},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["node_results"]) == 4
    for nr in data["node_results"].values():
        assert nr["status"] == "completed"


@pytest.mark.asyncio
async def test_validate_graph(async_client, admin_token_headers):
    payload = {
        "name": "validate-test",
        "nodes": [
            {"id": "a", "type": "worker", "name": "A"},
            {"id": "b", "type": "worker", "name": "B"},
            {"id": "c", "type": "reviewer", "name": "C"},
        ],
        "edges": [
            {"source": "a", "target": "c"},
            {"source": "b", "target": "c"},
        ],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/validate",
        json=payload,
        headers=admin_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["node_count"] == 3
    assert data["edge_count"] == 2
    assert data["topological_order"] is not None


@pytest.mark.asyncio
async def test_validate_graph_with_cycle(async_client, admin_token_headers):
    payload = {
        "name": "cycle-test",
        "nodes": [
            {"id": "a", "type": "worker", "name": "A"},
            {"id": "b", "type": "worker", "name": "B"},
        ],
        "edges": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
        ],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/validate",
        json=payload,
        headers=admin_token_headers,
    )
    assert resp.status_code == 400
    assert "cycle" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_runs(async_client, admin_token_headers):
    resp = await async_client.get(
        "/admin/agents/graphs/runs",
        headers=admin_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_run(async_client, admin_token_headers):
    # First create a run
    payload = {
        "name": "get-run-test",
        "nodes": [{"id": "n1", "type": "worker", "name": "Node 1"}],
        "edges": [],
    }
    create_resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": payload},
        headers=admin_token_headers,
    )
    assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
    run_id = create_resp.json()["run_id"]

    resp = await async_client.get(
        f"/admin/agents/graphs/runs/{run_id}",
        headers=admin_token_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id


@pytest.mark.asyncio
async def test_run_with_global_input(async_client, admin_token_headers):
    payload = {
        "name": "input-test",
        "nodes": [{"id": "n1", "type": "worker", "name": "Worker"}],
        "edges": [],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": payload},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_duplicate_node_id(async_client, admin_token_headers):
    payload = {
        "name": "duplicate-test",
        "nodes": [
            {"id": "same-id", "type": "worker", "name": "A"},
            {"id": "same-id", "type": "worker", "name": "B"},
        ],
        "edges": [],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/validate",
        json=payload,
        headers=admin_token_headers,
    )
    assert resp.status_code == 400
    assert "Duplicate" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_all_node_types(async_client, admin_token_headers):
    nodes = [
        {"id": f"{nt}-1", "type": nt, "name": nt}
        for nt in ["supervisor", "worker", "reviewer", "planner", "crew", "hierarchical"]
    ]
    payload = {
        "name": "all-types",
        "nodes": nodes,
        "edges": [],
    }
    resp = await async_client.post(
        "/admin/agents/graphs/run",
        json={"graph": payload},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["node_results"]) == 6
