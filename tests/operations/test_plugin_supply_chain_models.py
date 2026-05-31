import pytest
from sqlalchemy import select

from app.models.client import Client
from app.models.operations.plugin_supply_chain import (
    DependencyGovernancePolicy,
    PluginArtifactLineage,
    PluginDependencyVerification,
    PluginProvenanceRecord,
    PluginSBOMPlaceholder,
    PluginSignedArtifact,
    PluginSupplyChainReceipt,
)
from app.models.operations.plugin_runtime import PluginABIContract


def test_plugin_supply_chain_models_exposed():
    assert PluginProvenanceRecord.__tablename__ == "plugin_provenance_records"
    assert PluginSBOMPlaceholder.__tablename__ == "plugin_sbom_placeholders"
    assert PluginArtifactLineage.__tablename__ == "plugin_artifact_lineage"
    assert DependencyGovernancePolicy.__tablename__ == "dependency_governance_policies"
    assert PluginDependencyVerification.__tablename__ == "plugin_dependency_verifications"
    assert PluginSignedArtifact.__tablename__ == "plugin_signed_artifact_placeholders"
    assert PluginSupplyChainReceipt.__tablename__ == "plugin_supply_chain_receipts"


@pytest.mark.asyncio
async def test_plugin_supply_chain_models_persist(session):
    client = Client(name="phase80-models")
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
    provenance = PluginProvenanceRecord(
        id="d" * 64,
        client_id=client.id,
        plugin_contract_id=contract.id,
        artifact_name="bundle",
        artifact_version="1.0.0",
        provenance_scope="plugin",
        provenance_status="proposed",
        provenance_hash="e" * 64,
        replay_safe=True,
        immutable_hash="f" * 64,
    )
    session.add(provenance)
    await session.commit()
    stored = (await session.execute(select(PluginProvenanceRecord))).scalar_one()
    assert stored.artifact_name == "bundle"
    assert stored.provenance_status == "proposed"


def test_phase_80_migration_present():
    content = open("control_plane/alembic/versions/phase80_plugin_supply_chain_provenance_sbom.py", "r", encoding="utf-8").read()
    assert "plugin_provenance_records" in content
    assert "plugin_supply_chain_receipts" in content
    assert "_uuid_type" in content
