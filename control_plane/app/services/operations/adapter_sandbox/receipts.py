import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes a deterministic hash for a payload."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def build_manifest_receipt(manifest: Any) -> Dict[str, Any]:
    """Builds a receipt for an adapter manifest registration."""
    m_dict = manifest if isinstance(manifest, dict) else {
        "id": str(manifest.id),
        "client_id": str(manifest.client_id),
        "adapter_name": manifest.adapter_name,
        "adapter_version": manifest.adapter_version,
        "manifest_hash": manifest.manifest_hash
    }
    payload_hash = compute_payload_hash(m_dict)
    
    return {
        "receipt_type": "adapter_manifest_registration",
        "client_id": m_dict["client_id"],
        "subject_id": m_dict["id"],
        "immutable_hash": hashlib.sha256(f"{m_dict['client_id']}:manifest:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "dry_run": True,
        "signature_placeholder": "SIG_ADAPTER_MANIFEST_V1",
        "generated_at": "2026-05-15T12:00:00Z"
    }

def build_sandbox_run_receipt(run: Any, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a receipt for a sandbox run."""
    payload = {
        "run_id": str(run.id),
        "manifest_id": str(run.manifest_id),
        "status": run.status,
        "results": results
    }
    payload_hash = compute_payload_hash(payload)
    client_id = str(run.client_id)
    
    return {
        "receipt_type": "adapter_sandbox_run",
        "client_id": client_id,
        "subject_id": str(run.id),
        "immutable_hash": hashlib.sha256(f"{client_id}:sandbox:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "dry_run": True,
        "signature_placeholder": "SIG_ADAPTER_SANDBOX_RUN_V1",
        "generated_at": "2026-05-15T12:00:00Z"
    }

def build_policy_violation_receipt(violation: Any) -> Dict[str, Any]:
    """Builds a receipt for a policy violation."""
    v_dict = violation if isinstance(violation, dict) else {
        "id": str(violation.id),
        "client_id": str(violation.client_id),
        "violation_type": violation.violation_type,
        "severity": violation.severity
    }
    payload_hash = compute_payload_hash(v_dict)
    
    return {
        "receipt_type": "adapter_policy_violation",
        "client_id": v_dict["client_id"],
        "subject_id": v_dict["id"],
        "immutable_hash": hashlib.sha256(f"{v_dict['client_id']}:violation:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "dry_run": True,
        "signature_placeholder": "SIG_ADAPTER_POLICY_VIOLATION_V1",
        "generated_at": "2026-05-15T12:00:00Z"
    }
