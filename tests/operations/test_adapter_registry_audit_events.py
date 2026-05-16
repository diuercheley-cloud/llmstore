import pytest
from app.services.operations.adapter_registry.audit_events import build_adapter_registry_audit_event

class TestAdapterRegistryAuditEvents:
    def test_build_audit_event(self):
        event = build_adapter_registry_audit_event("entry_registered", "client123", {"name": "test"})
        assert event["event_type"] == "adapter_registry_entry_registered"
        assert event["client_id"] == "client123"
        assert event["offline_compatible"] is True
        assert event["signature_placeholder"] == "audit_sig_placeholder"
