from app.services.operations.adapter_registry.audit_events import build_adapter_registry_audit_event
from app.utils.crypto_signer import sign_payload


class TestAdapterRegistryAuditEvents:
    def test_build_audit_event(self):
        event = build_adapter_registry_audit_event(
            "entry_registered", "client123", {"name": "test"}
        )
        assert event["event_type"] == "adapter_registry_entry_registered"
        assert event["client_id"] == "client123"
        assert event["offline_compatible"] is True
        assert event["signature"] == sign_payload("audit_sig")
