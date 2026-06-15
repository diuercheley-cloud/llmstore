import hashlib
import json
from datetime import UTC, datetime
from typing import Any

AUDIT_EVENT_TYPES = {
    "failure_signal_recorded",
    "failure_forecast_created",
    "failure_risk_assessment_created",
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _build_audit_event(
    *,
    event_type: str,
    client_id: str,
    subject_id: str,
    receipt_hash: str,
    summary: str,
) -> dict[str, Any]:
    if event_type not in AUDIT_EVENT_TYPES:
        raise ValueError(f"Unknown audit event type: {event_type!r}")

    content: dict[str, Any] = {
        "event_type": event_type,
        "client_id": client_id,
        "subject_id": subject_id,
        "receipt_hash": receipt_hash,
        "summary": summary,
    }

    body: dict[str, Any] = {
        **content,
        "generated_at": _now_iso(),
    }

    body["immutable_hash"] = _sha256(_canonical_json(content))
    return body


def build_failure_signal_recorded_event(receipt: dict[str, Any]) -> dict[str, Any]:
    return _build_audit_event(
        event_type="failure_signal_recorded",
        client_id=receipt.get("client_id", ""),
        subject_id=receipt.get("subject_id", ""),
        receipt_hash=receipt.get("receipt_hash", ""),
        summary="Failure signal recorded and receipt generated.",
    )


def build_failure_forecast_created_event(receipt: dict[str, Any]) -> dict[str, Any]:
    return _build_audit_event(
        event_type="failure_forecast_created",
        client_id=receipt.get("client_id", ""),
        subject_id=receipt.get("subject_id", ""),
        receipt_hash=receipt.get("receipt_hash", ""),
        summary="Failure forecast created and receipt generated.",
    )


def build_failure_risk_assessment_created_event(receipt: dict[str, Any]) -> dict[str, Any]:
    return _build_audit_event(
        event_type="failure_risk_assessment_created",
        client_id=receipt.get("client_id", ""),
        subject_id=receipt.get("subject_id", ""),
        receipt_hash=receipt.get("receipt_hash", ""),
        summary="Failure risk assessment created and receipt generated.",
    )
