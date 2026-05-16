import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SIGNATURE_PLACEHOLDER = "placeholder_ed25519"
DETERMINISTIC_VERSION = "v1"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signature_placeholder(payload_hash: str) -> str:
    return f"{SIGNATURE_PLACEHOLDER}_{_sha256(payload_hash + ':local')[:48]}"


def _payload_hash(*, fields: dict[str, Any]) -> str:
    return _sha256(_canonical_json(fields))


def build_failure_signal_receipt(signal: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic receipt for a recorded failure signal.

    The input *signal* dict is expected to contain at least the fields
    returned by the ``FailureSignal`` model or an equivalent normalized
    dict (``id``, ``client_id``, ``signal_type``, ``source_domain``,
    ``severity``, ``confidence``, ``observed_at``, ``payload_json``,
    ``immutable_hash``, ``previous_hash``).
    """
    client_id = str(signal.get("client_id", ""))
    subject_id = str(signal.get("id", ""))
    immutable_hash = signal.get("immutable_hash")
    previous_hash = signal.get("previous_hash")

    payload_fields = {
        "signal_type": signal.get("signal_type"),
        "source_domain": signal.get("source_domain"),
        "severity": signal.get("severity"),
        "confidence": signal.get("confidence"),
        "observed_at": str(signal.get("observed_at", "")),
    }

    if signal.get("payload_json") and not _is_sensitive(signal["payload_json"]):
        payload_fields["payload"] = signal["payload_json"]

    ph = _payload_hash(fields=payload_fields)

    receipt_body: dict[str, Any] = {
        "receipt_type": "failure_signal_recorded",
        "client_id": client_id,
        "subject_id": subject_id,
        "immutable_hash": immutable_hash,
        "previous_hash": previous_hash,
        "generated_at": _now_iso(),
        "deterministic_version": DETERMINISTIC_VERSION,
        "advisory_only": True,
        "payload_hash": ph,
        "signature_placeholder": _signature_placeholder(ph),
    }
    receipt_body["receipt_hash"] = _sha256(_canonical_json(receipt_body))
    return receipt_body


def build_failure_forecast_receipt(forecast: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic receipt for a created forecast.

    The input *forecast* dict is expected to match the output of
    ``DeterministicFailureForecastingEngine.forecast``.
    """
    client_id = str(forecast.get("client_id", ""))
    subject_id = str(forecast.get("forecast_type", "unknown"))
    immutable_hash = forecast.get("immutable_hash")
    previous_hash = forecast.get("previous_hash")

    payload_fields = {
        "forecast_type": forecast.get("forecast_type"),
        "risk_score": forecast.get("risk_score"),
        "confidence": forecast.get("confidence"),
        "deterministic_version": forecast.get("deterministic_version"),
        "input_hash": forecast.get("input_hash"),
    }

    ph = _payload_hash(fields=payload_fields)

    receipt_body: dict[str, Any] = {
        "receipt_type": "failure_forecast_created",
        "client_id": client_id,
        "subject_id": subject_id,
        "immutable_hash": immutable_hash,
        "previous_hash": previous_hash,
        "generated_at": _now_iso(),
        "deterministic_version": DETERMINISTIC_VERSION,
        "advisory_only": True,
        "payload_hash": ph,
        "signature_placeholder": _signature_placeholder(ph),
    }
    receipt_body["receipt_hash"] = _sha256(_canonical_json(receipt_body))
    return receipt_body


def build_failure_risk_assessment_receipt(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic receipt for a created risk assessment.

    The input *assessment* dict is expected to match the output of
    ``FailureRiskScoringService.build_assessment``.
    """
    client_id = str(assessment.get("client_id", ""))
    subject_id = str(assessment.get("risk_level", "unknown"))
    immutable_hash = assessment.get("immutable_hash")

    payload_fields = {
        "risk_level": assessment.get("risk_level"),
        "risk_score": assessment.get("risk_score"),
        "recommendation": assessment.get("recommendation"),
        "requires_approval": assessment.get("requires_approval"),
        "dry_run": assessment.get("dry_run"),
    }

    ph = _payload_hash(fields=payload_fields)

    receipt_body: dict[str, Any] = {
        "receipt_type": "failure_risk_assessment_created",
        "client_id": client_id,
        "subject_id": subject_id,
        "immutable_hash": immutable_hash,
        "previous_hash": None,
        "generated_at": _now_iso(),
        "deterministic_version": DETERMINISTIC_VERSION,
        "advisory_only": True,
        "payload_hash": ph,
        "signature_placeholder": _signature_placeholder(ph),
    }
    receipt_body["receipt_hash"] = _sha256(_canonical_json(receipt_body))
    return receipt_body


def _is_sensitive(payload: Any) -> bool:
    """Check if a payload should be excluded from plaintext receipt fields."""
    if not isinstance(payload, dict):
        return False
    key_str = " ".join(str(k).lower() for k in payload)
    sensitive_tokens = {"secret", "token", "password", "credential", "key", "auth"}
    return any(t in key_str for t in sensitive_tokens)
