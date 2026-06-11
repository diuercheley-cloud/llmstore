import uuid
import pytest
from app.services.agents.agent_graph.models import (
    AgentGraphSpec,
    AgentNode,
    AgentNodeType,
    GraphEdge,
    GraphExecutionStatus,
    NodeExecutionStatus,
)
from app.services.agents.agent_graph.engine import AgentGraphEngine


@pytest.fixture
def engine(tmp_path):
    return AgentGraphEngine(artifacts_dir=str(tmp_path / "agent-graphs"))


def make_graph(
    node_types: list[AgentNodeType],
    edges: list[tuple[str, str]] | None = None,
) -> AgentGraphSpec:
    nodes = [
        AgentNode(
            id=f"node-{i}",
            type=nt,
            name=f"{nt.value}-{i}",
            max_retries=1,
            timeout_seconds=30,
        )
        for i, nt in enumerate(node_types)
    ]
    edge_objs = []
    if edges:
        for s, t in edges:
            edge_objs.append(GraphEdge(source=s, target=t))
    return AgentGraphSpec(
        nodes=nodes,
        edges=edge_objs,
        name="test-graph",
        max_concurrency=5,
        enable_checkpointing=True,
    )


@pytest.mark.asyncio
async def test_simple_sequential_graph(engine):
    graph = make_graph(
        [AgentNodeType.PLANNER, AgentNodeType.WORKER, AgentNodeType.REVIEWER],
        edges=[("node-0", "node-1"), ("node-1", "node-2")],
    )
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED
    assert len(result.node_results) == 3
    for nr in result.node_results.values():
        assert nr.status == NodeExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_parallel_execution(engine):
    graph = make_graph(
        [
            AgentNodeType.SUPERVISOR,
            AgentNodeType.WORKER,
            AgentNodeType.WORKER,
            AgentNodeType.WORKER,
            AgentNodeType.REVIEWER,
        ],
        edges=[
            ("node-0", "node-1"),
            ("node-0", "node-2"),
            ("node-0", "node-3"),
            ("node-1", "node-4"),
            ("node-2", "node-4"),
            ("node-3", "node-4"),
        ],
    )
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED
    assert len(result.node_results) == 5
    assert all(
        nr.status == NodeExecutionStatus.COMPLETED
        for nr in result.node_results.values()
    )


@pytest.mark.asyncio
async def test_cycle_detection(engine):
    graph = make_graph(
        [AgentNodeType.WORKER, AgentNodeType.WORKER],
        edges=[("node-0", "node-1"), ("node-1", "node-0")],
    )
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.FAILED
    assert "cycle" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_single_node(engine):
    graph = make_graph([AgentNodeType.WORKER])
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED
    assert len(result.node_results) == 1


@pytest.mark.asyncio
async def test_cancellation(engine):
    graph = make_graph(
        [AgentNodeType.WORKER, AgentNodeType.WORKER],
        edges=[("node-0", "node-1")],
    )
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_retry_on_failure(engine):
    call_count = 0

    async def failing_runner(node, ctx):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Simulated transient failure")
        return {"status": "ok", "node_id": node.id}

    eng = AgentGraphEngine(
        artifacts_dir=str(engine.artifacts_dir),
        node_runner=failing_runner,
    )
    graph = make_graph([AgentNodeType.WORKER])
    result = await eng.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED
    nr = result.node_results["node-0"]
    assert nr.retry_attempts == 1


@pytest.mark.asyncio
async def test_max_retries_exceeded(engine):
    async def always_failing(node, ctx):
        raise ValueError("Always fails")

    eng = AgentGraphEngine(
        artifacts_dir=str(engine.artifacts_dir),
        node_runner=always_failing,
    )
    graph = make_graph([AgentNodeType.WORKER])
    graph.nodes[0].max_retries = 1
    result = await eng.execute(graph)
    assert result.status == GraphExecutionStatus.FAILED
    nr = result.node_results["node-0"]
    assert nr.status == NodeExecutionStatus.FAILED
    assert nr.retry_attempts == 1


@pytest.mark.asyncio
async def test_disconnected_nodes(engine):
    graph = make_graph(
        [AgentNodeType.WORKER, AgentNodeType.WORKER, AgentNodeType.WORKER],
        edges=[("node-0", "node-1")],
    )
    result = await engine.execute(graph)
    # node-0 -> node-1 is connected, node-2 is disconnected but still runs
    assert result.status == GraphExecutionStatus.COMPLETED
    assert len(result.node_results) == 3


@pytest.mark.asyncio
async def test_checkpoint_persistence(engine):
    graph = make_graph(
        [AgentNodeType.PLANNER, AgentNodeType.WORKER],
        edges=[("node-0", "node-1")],
    )
    result = await engine.execute(graph)
    assert result.status == GraphExecutionStatus.COMPLETED
    checkpoint_dir = engine.artifacts_dir / result.run_id / "checkpoints"
    assert checkpoint_dir.exists()
    checkpoints = list(checkpoint_dir.glob("checkpoint_*.json"))
    assert len(checkpoints) >= 1


@pytest.mark.asyncio
async def test_topological_sort(engine):
    graph = make_graph(
        [AgentNodeType.WORKER, AgentNodeType.WORKER, AgentNodeType.WORKER],
        edges=[("node-0", "node-2"), ("node-1", "node-2")],
    )
    order = engine.topological_sort(graph)
    assert order.index("node-0") < order.index("node-2")
    assert order.index("node-1") < order.index("node-2")


@pytest.mark.asyncio
async def test_result_persistence(engine):
    graph = make_graph([AgentNodeType.WORKER])
    result = await engine.execute(graph)
    loaded = engine.get_status(result.run_id)
    assert loaded is not None
    assert loaded.status == GraphExecutionStatus.COMPLETED
    assert loaded.run_id == result.run_id


@pytest.mark.asyncio
async def test_list_runs(engine):
    graph = make_graph([AgentNodeType.WORKER])
    r1 = await engine.execute(graph)
    r2 = await engine.execute(graph)
    runs = engine.list_runs()
    assert len(runs) >= 2
    run_ids = [r["run_id"] for r in runs]
    assert r1.run_id in run_ids
    assert r2.run_id in run_ids


@pytest.mark.asyncio
async def test_all_agent_node_types_execute(engine):
    for nt in AgentNodeType:
        graph = make_graph([nt])
        result = await engine.execute(graph)
        assert result.status == GraphExecutionStatus.COMPLETED, f"Failed for {nt}"
        assert result.node_results["node-0"].status == NodeExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_custom_runner_context(engine):
    async def custom(node, ctx):
        assert "global_input" in ctx
        assert "run_id" in ctx
        return {"from_global": ctx["global_input"].get("key")}

    eng = AgentGraphEngine(
        artifacts_dir=str(engine.artifacts_dir),
        node_runner=custom,
    )
    graph = make_graph([AgentNodeType.WORKER])
    result = await eng.execute(graph, global_input={"key": "value"})
    assert result.status == GraphExecutionStatus.COMPLETED
