import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes a deterministic hash for a payload."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def build_pre_execution_receipt(execution: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a receipt before execution starts."""
    payload_hash = compute_payload_hash(execution)
    client_id = execution.get("client_id", "unknown")
    
    return {
        "receipt_type": "remediation_pre_execution",
        "client_id": client_id,
        "subject_id": execution.get("id"),
        "immutable_hash": hashlib.sha256(f"{client_id}:pre:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": execution.get("deterministic_version", "v1"),
        "dry_run": execution.get("dry_run", True),
        "signature": "SIG_REMEDIATION_PRE_EXEC_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def build_post_execution_receipt(execution: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a receipt after execution completes."""
    payload = {
        "execution": execution,
        "results": results
    }
    payload_hash = compute_payload_hash(payload)
    client_id = execution.get("client_id", "unknown")
    
    return {
        "receipt_type": "remediation_post_execution",
        "client_id": client_id,
        "subject_id": execution.get("id"),
        "immutable_hash": hashlib.sha256(f"{client_id}:post:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": execution.get("deterministic_version", "v1"),
        "dry_run": execution.get("dry_run", True),
        "signature": "SIG_REMEDIATION_POST_EXEC_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def build_kill_switch_receipt(state: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a receipt for a kill-switch update."""
    payload_hash = compute_payload_hash(state)
    client_id = state.get("client_id", "unknown")
    
    return {
        "receipt_type": "remediation_kill_switch_update",
        "client_id": client_id,
        "subject_id": state.get("id"),
        "immutable_hash": hashlib.sha256(f"{client_id}:ks:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "dry_run": False,
        "signature": "SIG_REMEDIATION_KS_UPDATE_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def build_rollback_plan_receipt(rollback_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a receipt for a rollback plan."""
    payload_hash = compute_payload_hash(rollback_plan)
    client_id = rollback_plan.get("client_id", "unknown")
    
    return {
        "receipt_type": "remediation_rollback_plan_proposal",
        "client_id": client_id,
        "subject_id": rollback_plan.get("id"),
        "immutable_hash": hashlib.sha256(f"{client_id}:rb:{payload_hash}".encode("utf-8")).hexdigest(),
        "payload_hash": payload_hash,
        "deterministic_version": "v1",
        "dry_run": True,
        "signature": "SIG_REMEDIATION_ROLLBACK_PLAN_V1",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
