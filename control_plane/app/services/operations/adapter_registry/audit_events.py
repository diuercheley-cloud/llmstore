from typing import Any, Dict

def build_adapter_registry_audit_event(event_type: str, client_id: str, payload: Dict) -> Dict:
    """Builds a standardized audit event for the adapter registry."""
    return {
        "event_type": f"adapter_registry_{event_type}",
        "client_id": client_id,
        "payload": payload,
        "offline_compatible": True,
        "signature_placeholder": "audit_sig_placeholder"
    }
