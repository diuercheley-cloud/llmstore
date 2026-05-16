import json
import uuid

from app.services.operations.plugin_supply_chain.audit_events import build_plugin_supply_chain_audit_event
from app.services.operations.plugin_supply_chain.dependency_governance import DependencyGovernanceService
from app.services.operations.plugin_supply_chain.lineage_service import PluginArtifactLineageService
from app.services.operations.plugin_supply_chain.provenance_service import PluginProvenanceService
from app.services.operations.plugin_supply_chain.receipts import build_supply_chain_receipt
from app.services.operations.plugin_supply_chain.replay_verifier import PluginSupplyChainReplayVerifier
from app.services.operations.plugin_supply_chain.sbom_placeholder import PluginSBOMPlaceholderService


def _provenance_record():
    service = PluginProvenanceService()
    return service.create_provenance_record(
        {
            "client_id": uuid.uuid4(),
            "plugin_contract_id": "c" * 64,
            "artifact_name": "bundle",
            "artifact_version": "1.0.0",
            "provenance_scope": "plugin",
        }
    )


def test_provenance_and_replay_verification():
    record = _provenance_record()
    service = PluginProvenanceService()
    replay = PluginSupplyChainReplayVerifier()
    verification = service.verify_provenance(record)
    assert verification["verified"] is True
    assert verification["status"] == "verified"
    replay_check = replay.verify_provenance(record)
    assert replay_check["match"] is True


def test_sbom_placeholder_and_lineage_verification():
    record = _provenance_record()
    sbom_service = PluginSBOMPlaceholderService()
    lineage_service = PluginArtifactLineageService()
    placeholder = sbom_service.generate_sbom_placeholder(
        record,
        dependency_summary_json={"dependency_classes": ["local_static_module"]},
        denied_dependencies_json=[],
    )
    assert sbom_service.validate_sbom_placeholder(placeholder)["valid"] is True
    lineage = lineage_service.create_lineage(record, parent_artifact_hash="p" * 64)
    assert lineage_service.verify_lineage(lineage, record)["verified"] is True


def test_dependency_governance_blocks_denied_classes_and_requires_placeholder_signature():
    record = _provenance_record()
    governance = DependencyGovernanceService()
    policy = governance.create_policy(record.client_id)
    blocked = governance.verify_dependencies(
        record,
        {"dependency_classes": ["network_loaders", "local_static_module"]},
        policy,
        signature_placeholder=None,
    )
    summary = json.loads(blocked.dependency_summary)
    assert blocked.verification_status == "blocked"
    assert "network_loaders" in summary["denied_hits"]
    assert summary["no_real_execution"] is True
    assert summary["no_external_dependency_resolution"] is True


def test_receipts_and_audit_events_are_placeholder_only():
    record = _provenance_record()
    receipt = build_supply_chain_receipt("provenance_receipt", record, record.provenance_hash)
    audit = build_plugin_supply_chain_audit_event("provenance_created", str(record.client_id), {"token": "secret", "artifact_name": "bundle"})
    assert receipt.signature_placeholder.startswith("placeholder-signature:")
    assert audit["payload"]["token"] == "redacted"
