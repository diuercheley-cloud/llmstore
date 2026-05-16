from app.services.operations.plugin_runtime.audit_events import build_plugin_runtime_audit_event


def test_plugin_runtime_audit_event_sanitizes_payload():
    event = build_plugin_runtime_audit_event(
        "plugin_runtime_receipt_created",
        "client",
        {"secret_token": "value", "contract_id": "abc"},
    )
    assert event["payload"]["secret_token"] == "redacted"
    assert event["offline_compatible"] is True
