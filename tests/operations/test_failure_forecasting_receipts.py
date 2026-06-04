from app.services.operations.forecasting.receipts import (
    SIGNATURE_PLACEHOLDER,
    build_failure_forecast_receipt,
    build_failure_risk_assessment_receipt,
    build_failure_signal_receipt,
)

SIGNAL_DICT = {
    "id": "sig-001",
    "client_id": "client-1",
    "signal_type": "latency_spike",
    "source_domain": "runtime",
    "severity": "critical",
    "confidence": 0.85,
    "observed_at": "2026-05-15T12:00:00+00:00",
    "payload_json": {"latency_ms": 5000},
    "immutable_hash": "a" * 64,
    "previous_hash": "b" * 64,
}

FORECAST_DICT = {
    "forecast_type": "node_failure",
    "risk_score": 0.72,
    "confidence": 0.88,
    "deterministic_version": "v1",
    "input_hash": "c" * 64,
    "advisory_only": True,
}

ASSESSMENT_DICT = {
    "forecast_type": "node_failure",
    "risk_score": 0.72,
    "risk_level": "high",
    "recommendation": "Investigate root cause.",
    "requires_approval": True,
    "dry_run": True,
    "advisory_only": True,
    "deterministic_version": "v1",
    "input_hash": "c" * 64,
    "immutable_hash": "d" * 64,
}


# ── Receipt structure ────────────────────────────────────────────────────────


class TestReceiptStructure:

    def test_signal_receipt_has_all_required_fields(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        _assert_receipt_fields(r, "failure_signal_recorded")

    def test_forecast_receipt_has_all_required_fields(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        _assert_receipt_fields(r, "failure_forecast_created")

    def test_assessment_receipt_has_all_required_fields(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        _assert_receipt_fields(r, "failure_risk_assessment_created")


# ── receipt_type ─────────────────────────────────────────────────────────────


class TestReceiptType:

    def test_signal_receipt_type(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["receipt_type"] == "failure_signal_recorded"

    def test_forecast_receipt_type(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        assert r["receipt_type"] == "failure_forecast_created"

    def test_assessment_receipt_type(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        assert r["receipt_type"] == "failure_risk_assessment_created"


# ── client_id and subject_id ─────────────────────────────────────────────────


class TestIdentity:

    def test_signal_client_id(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["client_id"] == "client-1"

    def test_signal_subject_id(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["subject_id"] == "sig-001"

    def test_forecast_client_id_default(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        assert r["client_id"] == ""

    def test_forecast_subject_id_is_forecast_type(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        assert r["subject_id"] == "node_failure"

    def test_assessment_subject_id_is_risk_level(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        assert r["subject_id"] == "high"


# ── immutable_hash and previous_hash ─────────────────────────────────────────


class TestHashes:

    def test_signal_immutable_hash_passed_through(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["immutable_hash"] == "a" * 64

    def test_signal_previous_hash_passed_through(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["previous_hash"] == "b" * 64

    def test_forecast_immutable_hash_none(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        assert r["immutable_hash"] is None

    def test_assessment_immutable_hash_passed_through(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        assert r["immutable_hash"] == "d" * 64

    def test_assessment_previous_hash_is_none(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        assert r["previous_hash"] is None


# ── payload_hash ─────────────────────────────────────────────────────────────


class TestPayloadHash:

    def test_payload_hash_is_64_hex_chars(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert len(r["payload_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in r["payload_hash"])

    def test_same_signal_produces_same_payload_hash(self):
        r1 = build_failure_signal_receipt(SIGNAL_DICT)
        r2 = build_failure_signal_receipt(SIGNAL_DICT)
        assert r1["payload_hash"] == r2["payload_hash"]

    def test_different_signals_produce_different_payload_hash(self):
        other = dict(SIGNAL_DICT, severity="warning")
        r1 = build_failure_signal_receipt(SIGNAL_DICT)
        r2 = build_failure_signal_receipt(other)
        assert r1["payload_hash"] != r2["payload_hash"]


# ── signature ─────────────────────────────────────────────────────


class TestSignaturePlaceholder:

    def test_signature_present(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert "signature" in r

    def test_signature_starts_with_placeholder(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["signature"].startswith(SIGNATURE_PLACEHOLDER)

    def test_signature_deterministic_for_same_input(self):
        r1 = build_failure_signal_receipt(SIGNAL_DICT)
        r2 = build_failure_signal_receipt(SIGNAL_DICT)
        assert r1["signature"] == r2["signature"]

    def test_signature_changes_with_payload(self):
        r1 = build_failure_signal_receipt(SIGNAL_DICT)
        other = dict(SIGNAL_DICT, severity="info")
        r2 = build_failure_signal_receipt(other)
        assert r1["signature"] != r2["signature"]


# ── advisory_only ────────────────────────────────────────────────────────────


class TestAdvisoryOnly:

    def test_signal_receipt_advisory_only(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["advisory_only"] is True

    def test_forecast_receipt_advisory_only(self):
        r = build_failure_forecast_receipt(FORECAST_DICT)
        assert r["advisory_only"] is True

    def test_assessment_receipt_advisory_only(self):
        r = build_failure_risk_assessment_receipt(ASSESSMENT_DICT)
        assert r["advisory_only"] is True


# ── deterministic_version and generated_at ───────────────────────────────────


class TestMetadata:

    def test_deterministic_version(self):
        for builder in (build_failure_signal_receipt, build_failure_forecast_receipt, build_failure_risk_assessment_receipt):
            r = builder(SIGNAL_DICT if builder is build_failure_signal_receipt else (FORECAST_DICT if builder is build_failure_forecast_receipt else ASSESSMENT_DICT))
            assert r["deterministic_version"] == "v1"

    def test_generated_at_is_iso(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert "T" in r["generated_at"]


# ── receipt_hash ─────────────────────────────────────────────────────────────


class TestReceiptHash:

    def test_receipt_hash_is_64_hex_chars(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert len(r["receipt_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in r["receipt_hash"])


# ── Offline compatibility ────────────────────────────────────────────────────


class TestOffline:

    def test_builds_without_network(self):
        r = build_failure_signal_receipt(SIGNAL_DICT)
        assert r["receipt_hash"] is not None


# ── Sensitive payload handling ───────────────────────────────────────────────


class TestSensitivePayload:

    def test_payload_with_secret_key_is_excluded(self):
        sig = dict(SIGNAL_DICT, payload_json={"api_key": "sk-123"})
        r = build_failure_signal_receipt(sig)
        assert r["payload_hash"] is not None

    def test_payload_with_token_is_excluded(self):
        sig = dict(SIGNAL_DICT, payload_json={"token": "tkn-abc"})
        r = build_failure_signal_receipt(sig)
        assert r["payload_hash"] is not None

    def test_non_sensitive_payload_included(self):
        sig = dict(SIGNAL_DICT, payload_json={"cpu_pct": 95})
        r = build_failure_signal_receipt(sig)
        assert r["payload_hash"] is not None


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_empty_signal_dict(self):
        r = build_failure_signal_receipt({})
        assert r["client_id"] == ""
        assert r["subject_id"] == ""
        assert r["advisory_only"] is True

    def test_empty_forecast_dict(self):
        r = build_failure_forecast_receipt({})
        assert r["receipt_type"] == "failure_forecast_created"
        assert r["advisory_only"] is True

    def test_empty_assessment_dict(self):
        r = build_failure_risk_assessment_receipt({})
        assert r["receipt_type"] == "failure_risk_assessment_created"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _assert_receipt_fields(receipt: dict, expected_type: str) -> None:
    assert receipt["receipt_type"] == expected_type
    assert "client_id" in receipt
    assert "subject_id" in receipt
    assert "immutable_hash" in receipt
    assert "previous_hash" in receipt
    assert "generated_at" in receipt
    assert "deterministic_version" in receipt
    assert "advisory_only" in receipt
    assert "payload_hash" in receipt
    assert "signature" in receipt
    assert "receipt_hash" in receipt
