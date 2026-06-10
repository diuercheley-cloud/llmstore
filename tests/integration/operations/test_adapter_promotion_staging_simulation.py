import uuid

from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.services.operations.adapter_promotion.staging_simulation import (
    AdapterStagingSimulationService,
)


def test_staging_simulation_logic():
    service = AdapterStagingSimulationService()
    assert service.require_staging_simulation("production_eligible") is True
    assert service.require_staging_simulation("sandboxed") is False
    
    client_id = uuid.uuid4()
    entry = SignedAdapterRegistryEntry(
        client_id=client_id,
        adapter_name="test",
        adapter_version="1.0.0",
        manifest_hash="mhash"
    )
    
    context_ok = {"staging_simulation_passed": True}
    assert service.validate_staging_simulation(entry, context_ok) is True
    
    summary = service.build_staging_simulation_summary(entry, context_ok)
    assert summary["result"] == "success"
    assert "verifiable_markers" in summary
