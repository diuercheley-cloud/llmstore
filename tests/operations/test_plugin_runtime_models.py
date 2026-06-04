import pytest
from app.models.client import Client
from app.models.operations.plugin_runtime import (
    DeterministicExtensionLoadPlan,
    PluginABIContract,
    PluginCapabilityBoundary,
    PluginFederationCompatibility,
    PluginIsolationPolicy,
    PluginLifecycleEvent,
    PluginReplayVerificationResult,
    PluginRuntimeCompatibilityCheck,
    PluginRuntimeReceipt,
)
from sqlalchemy import select


def test_plugin_runtime_models_exposed():
    assert PluginABIContract.__tablename__ == "plugin_abi_contracts"
    assert PluginCapabilityBoundary.__tablename__ == "plugin_capability_boundaries"
    assert PluginRuntimeCompatibilityCheck.__tablename__ == "plugin_runtime_compatibility_checks"
    assert DeterministicExtensionLoadPlan.__tablename__ == "deterministic_extension_load_plans"
    assert PluginIsolationPolicy.__tablename__ == "plugin_isolation_policies"
    assert PluginLifecycleEvent.__tablename__ == "plugin_lifecycle_events"
    assert PluginReplayVerificationResult.__tablename__ == "plugin_replay_verification_results"
    assert PluginFederationCompatibility.__tablename__ == "plugin_federation_compatibility"
    assert PluginRuntimeReceipt.__tablename__ == "plugin_runtime_receipts"


@pytest.mark.asyncio
async def test_plugin_runtime_models_persist(session):
    client = Client(name="phase79-models")
    session.add(client)
    await session.flush()
    contract = PluginABIContract(
        id="c" * 64,
        client_id=client.id,
        plugin_name="plugin",
        plugin_version="1.0.0",
        abi_version="1.0.0",
        schema_version="1.0.0",
        contract_scope="workflow",
        contract_status="active",
        deterministic_version="v1",
        contract_hash="a" * 64,
        immutable_hash="b" * 64,
    )
    session.add(contract)
    await session.commit()
    stored = (await session.execute(select(PluginABIContract))).scalar_one()
    assert stored.plugin_name == "plugin"
    assert stored.contract_status == "active"


def test_phase_79_migration_present():
    content = open("control_plane/alembic/versions/phase79_formal_plugin_abi_runtime.py", "r", encoding="utf-8").read()
    assert "plugin_abi_contracts" in content
    assert "plugin_runtime_receipts" in content
