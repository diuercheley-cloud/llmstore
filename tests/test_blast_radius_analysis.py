import pytest

from app.services.governance.blast_radius_analysis import BlastRadiusAnalysisService


def test_blast_radius_score_is_deterministic():
    service = BlastRadiusAnalysisService()
    request = {
        "action_type": "federation_sync",
        "target_type": "cluster",
        "target_id": "cluster-a",
        "tenant_id": "tenant-a",
        "affected_tenants": ["tenant-a", "tenant-b"],
        "target_clusters": ["cluster-a", "cluster-b"],
        "runtime_nodes": ["node-1", "node-2"],
        "federation_scope": True,
    }

    first = service.score_request(request)
    second = service.score_request(dict(request))

    assert first["blast_radius_score"] == second["blast_radius_score"]
    assert first["reproducibility_hash"] == second["reproducibility_hash"]
    assert first["severity"] == "critical"


@pytest.mark.asyncio
async def test_blast_radius_record_is_deduplicated(session):
    service = BlastRadiusAnalysisService()
    request = {
        "action_type": "safe_throttle",
        "target_type": "runtime_node",
        "target_id": "node-1",
        "tenant_id": "tenant-a",
        "runtime_nodes": ["node-1"],
    }

    first = await service.analyze_and_record(session, request=request)
    second = await service.analyze_and_record(session, request=request)

    assert first.id == second.id
    assert first.reproducibility_hash == second.reproducibility_hash
