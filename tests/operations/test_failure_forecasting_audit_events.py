import pytest

from app.services.operations.forecasting.audit_events import (
    build_failure_signal_recorded_event,
    build_failure_forecast_created_event,
    build_failure_risk_assessment_created_event,
    AUDIT_EVENT_TYPES,
)

SIGNAL_RECEIPT = {
    "receipt_type": "failure_signal_recorded",
    "client_id": "client-1",
    "subject_id": "sig-001",
    "receipt_hash": "a" * 64,
}

FORECAST_RECEIPT = {
    "receipt_type": "failure_forecast_created",
    "client_id": "client-2",
    "subject_id": "node_failure",
    "receipt_hash": "b" * 64,
}

ASSESSMENT_RECEIPT = {
    "receipt_type": "failure_risk_assessment_created",
    "client_id": "client-3",
    "subject_id": "high",
    "receipt_hash": "c" * 64,
}


# ── Event structure ──────────────────────────────────────────────────────────


class TestEventStructure:

    def test_signal_event_contains_all_required_fields(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        _assert_event_fields(e, "failure_signal_recorded")

    def test_forecast_event_contains_all_required_fields(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        _assert_event_fields(e, "failure_forecast_created")

    def test_assessment_event_contains_all_required_fields(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        _assert_event_fields(e, "failure_risk_assessment_created")


# ── Event type ───────────────────────────────────────────────────────────────


class TestEventType:

    def test_signal_event_type(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e["event_type"] == "failure_signal_recorded"

    def test_forecast_event_type(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert e["event_type"] == "failure_forecast_created"

    def test_assessment_event_type(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        assert e["event_type"] == "failure_risk_assessment_created"

    def test_all_event_types_registered(self):
        types_from_functions = {
            build_failure_signal_recorded_event(SIGNAL_RECEIPT)["event_type"],
            build_failure_forecast_created_event(FORECAST_RECEIPT)["event_type"],
            build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)["event_type"],
        }
        assert types_from_functions == AUDIT_EVENT_TYPES


# ── Identity propagation ─────────────────────────────────────────────────────


class TestIdentityPropagation:

    def test_signal_event_client_id(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e["client_id"] == "client-1"

    def test_signal_event_subject_id(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e["subject_id"] == "sig-001"

    def test_forecast_event_client_id(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert e["client_id"] == "client-2"

    def test_forecast_event_subject_id(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert e["subject_id"] == "node_failure"

    def test_assessment_event_client_id(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        assert e["client_id"] == "client-3"

    def test_assessment_event_subject_id(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        assert e["subject_id"] == "high"


# ── receipt_hash ─────────────────────────────────────────────────────────────


class TestReceiptHash:

    def test_signal_event_receipt_hash(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e["receipt_hash"] == "a" * 64

    def test_forecast_event_receipt_hash(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert e["receipt_hash"] == "b" * 64

    def test_assessment_event_receipt_hash(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        assert e["receipt_hash"] == "c" * 64


# ── immutable_hash ───────────────────────────────────────────────────────────


class TestImmutableHash:

    def test_immutable_hash_is_64_hex_chars(self):
        for builder in (build_failure_signal_recorded_event, build_failure_forecast_created_event, build_failure_risk_assessment_created_event):
            e = builder(SIGNAL_RECEIPT if "signal" in builder.__name__ else (FORECAST_RECEIPT if "forecast" in builder.__name__ else ASSESSMENT_RECEIPT))
            assert len(e["immutable_hash"]) == 64
            assert all(c in "0123456789abcdef" for c in e["immutable_hash"])

    def test_immutable_hash_deterministic(self):
        e1 = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        e2 = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e1["immutable_hash"] == e2["immutable_hash"]

    def test_different_events_have_different_hashes(self):
        e1 = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        e2 = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert e1["immutable_hash"] != e2["immutable_hash"]


# ── generated_at ─────────────────────────────────────────────────────────────


class TestGeneratedAt:

    def test_generated_at_is_iso_format(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert "T" in e["generated_at"]


# ── Summary ──────────────────────────────────────────────────────────────────


class TestSummary:

    def test_signal_event_summary(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert isinstance(e["summary"], str)
        assert "signal" in e["summary"].lower()

    def test_forecast_event_summary(self):
        e = build_failure_forecast_created_event(FORECAST_RECEIPT)
        assert isinstance(e["summary"], str)
        assert "forecast" in e["summary"].lower()

    def test_assessment_event_summary(self):
        e = build_failure_risk_assessment_created_event(ASSESSMENT_RECEIPT)
        assert isinstance(e["summary"], str)
        assert "assessment" in e["summary"].lower()


# ── Offline compatibility ────────────────────────────────────────────────────


class TestOffline:

    def test_event_produced_without_network(self):
        e = build_failure_signal_recorded_event(SIGNAL_RECEIPT)
        assert e["event_type"] is not None
        assert e["immutable_hash"] is not None


# ── Rejects invalid type ─────────────────────────────────────────────────────


class TestValidation:

    def test_invalid_event_type_raises(self):
        from app.services.operations.forecasting.audit_events import _build_audit_event

        with pytest.raises(ValueError, match="Unknown audit event type"):
            _build_audit_event(
                event_type="invalid_type",
                client_id="x",
                subject_id="y",
                receipt_hash="z",
                summary="bad",
            )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _assert_event_fields(event: dict, expected_type: str) -> None:
    assert event["event_type"] == expected_type
    assert "client_id" in event
    assert "subject_id" in event
    assert "receipt_hash" in event
    assert "summary" in event
    assert "generated_at" in event
    assert "immutable_hash" in event
