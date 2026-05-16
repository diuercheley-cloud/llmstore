import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes a deterministic hash for a payload."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def build_remediation_plan_receipt(plan: Dict[str, Any], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a receipt for a remediation plan."""
    payload = {
        "plan": plan,
        "steps": steps
    }
    payload_hash = compute_payload_hash(payload)
    
    # Immutable hash includes client_id if available, otherwise just payload
    client_id = plan.get("client_id", "unknown")
    immutable_hash = hashlib.sha256(f"{client_id}:{payload_hash}".encode("utf-8")).hexdigest()
    
    return {
        "receipt_type": "remediation_plan_proposal",
        "client_id": client_id,
        "subject_id": plan.get("id"),
        "immutable_hash": immutable_hash,
        "payload_hash": payload_hash,
        "deterministic_version": plan.get("deterministic_version", "v1"),
        "advisory_only": True,
        "dry_run": plan.get("dry_run", True),
        "signature_placeholder": "SIG_REMEDIATION_PLAN_PROPOSAL_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def build_remediation_step_receipt(step: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a receipt for a remediation step."""
    payload_hash = compute_payload_hash(step)
    client_id = step.get("client_id", "unknown")
    immutable_hash = hashlib.sha256(f"{client_id}:{payload_hash}".encode("utf-8")).hexdigest()
    
    return {
        "receipt_type": "remediation_step_proposal",
        "client_id": client_id,
        "subject_id": step.get("id"),
        "immutable_hash": immutable_hash,
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "advisory_only": True,
        "dry_run": step.get("dry_run", True),
        "signature_placeholder": "SIG_REMEDIATION_STEP_PROPOSAL_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def build_approval_requirement_receipt(requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a receipt for an approval requirement."""
    payload_hash = compute_payload_hash(requirement)
    client_id = requirement.get("client_id", "unknown")
    immutable_hash = hashlib.sha256(f"{client_id}:{payload_hash}".encode("utf-8")).hexdigest()
    
    return {
        "receipt_type": "remediation_approval_requirement",
        "client_id": client_id,
        "subject_id": requirement.get("id"),
        "immutable_hash": immutable_hash,
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "advisory_only": True,
        "dry_run": True,
        "signature_placeholder": "SIG_REMEDIATION_APPROVAL_REQ_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
