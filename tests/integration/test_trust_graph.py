import pytest
from app.services.security.trust_graph import TrustGraphService


@pytest.mark.asyncio
async def test_trust_graph_add_node(session):
    service = TrustGraphService()
    node = await service.add_node(session, "runtime", "Test Node", {"version": "1.0"})
    
    assert node.id is not None
    assert node.node_type == "runtime"
    assert node.label == "Test Node"
    assert node.hash is not None

@pytest.mark.asyncio
async def test_trust_graph_add_edge(session):
    service = TrustGraphService()
    node1 = await service.add_node(session, "governance", "Policy A", {})
    node2 = await service.add_node(session, "runtime", "Execution B", {})
    
    edge = await service.add_edge(session, node1.id, node2.id, "dependency", {"rule": "must_follow"})
    
    assert edge.id is not None
    assert edge.source_node_id == node1.id
    assert edge.target_node_id == node2.id
    assert edge.hash is not None

@pytest.mark.asyncio
async def test_trust_graph_integrity(session):
    service = TrustGraphService()
    node = await service.add_node(session, "runtime", "Integrity Node", {"data": 123})
    
    # Verify initially healthy
    violations = await service.verify_graph_integrity(session)
    assert len(violations) == 0
    
    # Manually corrupt node hash (simulating tampering)
    node.hash = "tampered_hash"
    session.add(node)
    await session.commit()
    
    violations = await service.verify_graph_integrity(session)
    assert len(violations) > 0
    assert violations[0]["type"] == "node_hash_mismatch"


@pytest.mark.asyncio
async def test_trust_graph_is_deterministic(session):
    service = TrustGraphService()
    await service.add_node(session, "runtime", "Node A", {"tenant_id": "tenant-a"})
    await service.add_node(session, "governance", "Policy A", {"status": "active"})

    graph1 = await service.get_full_graph(session)
    graph2 = await service.get_full_graph(session)

    assert graph1["graph_hash"] == graph2["graph_hash"]
    assert graph1["merkle_root"] == graph2["merkle_root"]


@pytest.mark.asyncio
async def test_trust_graph_lineage(session):
    service = TrustGraphService()
    source = await service.add_node(session, "governance", "Source", {})
    target = await service.add_node(session, "runtime", "Target", {})
    await service.add_edge(session, source.id, target.id, "runtime_trust_propagation", {"scope": "test"})

    lineage = await service.get_node_lineage(session, node_id=str(target.id))

    assert lineage["found"] is True
    assert len(lineage["nodes"]) >= 2
    assert any(edge["type"] == "runtime_trust_propagation" for edge in lineage["edges"])
