import pytest
from app.services.security.trust_graph import TrustGraphService
from app.services.security.trust_violation_detection import TrustViolationDetectionService


@pytest.mark.asyncio
async def test_run_detection(session):
    graph_service = TrustGraphService()
    violation_service = TrustViolationDetectionService()

    # Add a node and corrupt it
    node = await graph_service.add_node(session, "runtime", "Corrupt Node", {})
    node.hash = "invalid_hash"
    session.add(node)
    await session.commit()

    violations = await violation_service.run_detection(session)
    assert len(violations) > 0
    assert violations[0].violation_type == "node_hash_mismatch"


@pytest.mark.asyncio
async def test_get_active_violations(session):
    violation_service = TrustViolationDetectionService()

    # Initially no active violations
    active = await violation_service.get_active_violations(session)
    assert len(active) == 0

    # Run detection (assuming something is corrupt from previous tests or manually added)
    # For a clean test, let's manually add one
    from app.models.commercial.commercial_trust_violation import CommercialTrustViolation

    v = CommercialTrustViolation(violation_type="test_violation", severity="low")
    session.add(v)
    await session.commit()

    active = await violation_service.get_active_violations(session)
    assert len(active) > 0


@pytest.mark.asyncio
async def test_detects_tenant_isolation_violation(session):
    graph_service = TrustGraphService()
    violation_service = TrustViolationDetectionService()

    source = await graph_service.add_node(
        session, "workflow", "Tenant A", {"tenant_id": "tenant-a"}
    )
    target = await graph_service.add_node(
        session, "workflow", "Tenant B", {"tenant_id": "tenant-b"}
    )
    await graph_service.add_edge(session, source.id, target.id, "dependency_integrity", {})

    violations = await violation_service.run_detection(session)

    assert any(item.violation_type == "tenant_isolation_violation" for item in violations)
