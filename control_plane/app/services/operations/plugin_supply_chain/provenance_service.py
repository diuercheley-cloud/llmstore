from typing import Any

from app.models.operations.plugin_supply_chain import (
    PLUGIN_PROVENANCE_SCOPES,
    PLUGIN_PROVENANCE_STATUSES,
    PluginProvenanceRecord,
)
from app.services.operations.plugin_supply_chain.hash_utils import (
    compute_provenance_hash,
    sha256_hex,
)


class PluginProvenanceService:
    def create_provenance_record(self, payload: dict[str, Any]) -> PluginProvenanceRecord:
        if payload["provenance_scope"] not in PLUGIN_PROVENANCE_SCOPES:
            raise ValueError("unsupported provenance scope")
        status = payload.get("provenance_status", "proposed")
        if status not in PLUGIN_PROVENANCE_STATUSES:
            raise ValueError("unsupported provenance status")
        logical_payload = {
            "client_id": str(payload["client_id"]),
            "plugin_contract_id": payload["plugin_contract_id"],
            "artifact_name": payload["artifact_name"],
            "artifact_version": payload["artifact_version"],
            "provenance_scope": payload["provenance_scope"],
            "replay_safe": payload.get("replay_safe", True),
        }
        provenance_hash = compute_provenance_hash(logical_payload)
        immutable_hash = sha256_hex({"kind": "plugin_supply_chain_provenance_immutable", "provenance_hash": provenance_hash})
        record = PluginProvenanceRecord(
            id=sha256_hex({"kind": "plugin_supply_chain_provenance_id", **logical_payload}),
            client_id=payload["client_id"],
            plugin_contract_id=payload["plugin_contract_id"],
            artifact_name=payload["artifact_name"],
            artifact_version=payload["artifact_version"],
            provenance_scope=payload["provenance_scope"],
            provenance_status=status,
            provenance_hash=provenance_hash,
            replay_safe=payload.get("replay_safe", True),
            immutable_hash=immutable_hash,
        )
        record._logical_payload = logical_payload
        return record

    def verify_provenance(self, record: PluginProvenanceRecord) -> dict[str, Any]:
        logical_payload = getattr(record, "_logical_payload", None) or {
            "client_id": str(record.client_id),
            "plugin_contract_id": record.plugin_contract_id,
            "artifact_name": record.artifact_name,
            "artifact_version": record.artifact_version,
            "provenance_scope": record.provenance_scope,
            "replay_safe": record.replay_safe,
        }
        replayed_hash = compute_provenance_hash(logical_payload)
        verified = replayed_hash == record.provenance_hash and record.provenance_status != "revoked"
        record.provenance_status = "verified" if verified else "warning"
        return {
            "verified": verified,
            "replay_safe": record.replay_safe and verified,
            "original_hash": record.provenance_hash,
            "replayed_hash": replayed_hash,
            "status": record.provenance_status,
        }

    def revoke_provenance(self, record: PluginProvenanceRecord, reason: str = "manual revoke") -> dict[str, Any]:
        record.provenance_status = "revoked"
        return {
            "status": record.provenance_status,
            "reason": reason,
            "replay_safe": False,
        }

    def explain_provenance(self, record: PluginProvenanceRecord) -> dict[str, Any]:
        return {
            "artifact": f"{record.artifact_name}:{record.artifact_version}",
            "scope": record.provenance_scope,
            "status": record.provenance_status,
            "replay_safe": record.replay_safe,
            "offline_first": True,
            "federation_safe_provenance": record.provenance_scope != "plugin" or record.replay_safe,
            "notes": [
                "offline-first provenance only",
                "no real artifact signing",
                "deterministic provenance record only",
            ],
        }
