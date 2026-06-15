from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_attestation_runtime import (
    CommercialAttestationChallenge,
    CommercialRuntimeAttestation,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_payload(payload: dict[str, Any]) -> str:
    return _hash_bytes(_canonical_json(payload).encode("utf-8"))


def _generate_nonce() -> str:
    return secrets.token_hex(32)


def _is_challenge_expired(challenge: CommercialAttestationChallenge) -> bool:
    return challenge.expires_at is not None and challenge.expires_at < utc_now()


async def issue_challenge(
    db: AsyncSession,
    *,
    cluster_id: str,
    node_id: str | None = None,
    tenant_id: str | None = None,
    challenge_type: str = "runtime_measurement",
    required_measurements: list[str] | None = None,
    trust_score_required: float = 0.0,
    ttl_seconds: int | None = None,
) -> CommercialAttestationChallenge:
    settings = get_settings()
    effective_ttl = ttl_seconds or settings.commercial_runtime_attestation_challenge_ttl_seconds

    nonce = _generate_nonce()
    challenge_data = sanitize_report_payload(
        {
            "nonce": nonce,
            "type": challenge_type,
            "required_measurements": required_measurements or [],
            "trust_score_required": trust_score_required,
            "issued_at": utc_now().isoformat(),
            "ttl_seconds": effective_ttl,
        }
    )

    record = CommercialAttestationChallenge(
        node_id=node_id,
        cluster_id=cluster_id,
        tenant_id=tenant_id,
        challenge_nonce=nonce,
        challenge_type=challenge_type,
        challenge_data_json=challenge_data,
        response_data_json={},
        status="pending",
        response_received=False,
        response_valid=False,
        required_measurements_json=required_measurements or [],
        trust_score_required=trust_score_required,
        issued_at=utc_now(),
        expires_at=utc_now() + timedelta(seconds=effective_ttl),
    )
    db.add(record)
    await db.flush()
    return record


async def respond_to_challenge(
    db: AsyncSession,
    challenge_id: uuid.UUID,
    response_data: dict[str, Any],
    *,
    attestation_id: uuid.UUID | None = None,
) -> CommercialAttestationChallenge:
    challenge = await db.get(CommercialAttestationChallenge, challenge_id)
    if not challenge:
        raise ValueError("Challenge not found")

    if _is_challenge_expired(challenge):
        challenge.status = "expired"
        challenge.response_valid = False
        await db.flush()
        raise ValueError("Challenge has expired")

    if challenge.response_received:
        raise ValueError("Challenge already responded to (replay protection)")

    sanitized_response = sanitize_report_payload(response_data)
    challenge.response_data_json = sanitized_response
    challenge.response_received = True
    challenge.responded_at = utc_now()

    is_valid = await _verify_challenge_response(
        db,
        challenge,
        sanitized_response,
        attestation_id=attestation_id,
    )

    challenge.response_valid = is_valid
    challenge.status = "verified" if is_valid else "failed"
    if is_valid:
        challenge.verification_result = "passed"
    else:
        challenge.verification_result = "failed"

    await db.flush()
    return challenge


async def _verify_challenge_response(
    db: AsyncSession,
    challenge: CommercialAttestationChallenge,
    response: dict[str, Any],
    *,
    attestation_id: uuid.UUID | None = None,
) -> bool:
    nonce = challenge.challenge_data_json.get("nonce")
    response_nonce = response.get("nonce")
    if not nonce or nonce != response_nonce:
        return False

    response_hash = response.get("response_hash")
    if not response_hash:
        return False

    if attestation_id:
        attestation = await db.get(CommercialRuntimeAttestation, attestation_id)
        if not attestation:
            return False
        expected_hash = attestation.evidence_hash
        if response_hash != expected_hash:
            return False

    required_measurements = challenge.required_measurements_json or []
    provided_measurements = response.get("measurements", [])
    for req in required_measurements:
        if req not in provided_measurements:
            return False

    return True


async def verify_challenge(
    db: AsyncSession,
    challenge_id: uuid.UUID,
) -> CommercialAttestationChallenge:
    challenge = await db.get(CommercialAttestationChallenge, challenge_id)
    if not challenge:
        raise ValueError("Challenge not found")
    if _is_challenge_expired(challenge):
        challenge.status = "expired"
        challenge.response_valid = False
        await db.flush()
        return challenge
    if not challenge.response_received:
        challenge.verification_result = "no_response"
        challenge.status = "pending"
        await db.flush()
        return challenge
    return challenge


async def expire_stale_challenges(db: AsyncSession) -> int:
    result = await db.execute(
        select(CommercialAttestationChallenge).where(
            CommercialAttestationChallenge.status == "pending",
            CommercialAttestationChallenge.expires_at < utc_now(),
        )
    )
    stale = result.scalars().all()
    for challenge in stale:
        challenge.status = "expired"
    await db.flush()
    return len(stale)


async def revoke_challenge(
    db: AsyncSession,
    challenge_id: uuid.UUID,
) -> CommercialAttestationChallenge:
    challenge = await db.get(CommercialAttestationChallenge, challenge_id)
    if not challenge:
        raise ValueError("Challenge not found")
    challenge.status = "revoked"
    await db.flush()
    return challenge


async def summarize_challenges(db: AsyncSession) -> dict[str, Any]:
    total = (await db.execute(select(func.count(CommercialAttestationChallenge.id)))).scalar() or 0
    pending = (
        await db.execute(
            select(func.count(CommercialAttestationChallenge.id)).where(
                CommercialAttestationChallenge.status == "pending"
            )
        )
    ).scalar() or 0
    verified = (
        await db.execute(
            select(func.count(CommercialAttestationChallenge.id)).where(
                CommercialAttestationChallenge.status == "verified"
            )
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(CommercialAttestationChallenge.id)).where(
                CommercialAttestationChallenge.status == "failed"
            )
        )
    ).scalar() or 0
    expired = (
        await db.execute(
            select(func.count(CommercialAttestationChallenge.id)).where(
                CommercialAttestationChallenge.status == "expired"
            )
        )
    ).scalar() or 0

    recent = await db.execute(
        select(CommercialAttestationChallenge)
        .order_by(CommercialAttestationChallenge.created_at.desc())
        .limit(20)
    )
    items = recent.scalars().all()

    return {
        "total_challenges": int(total),
        "pending": int(pending),
        "verified": int(verified),
        "failed": int(failed),
        "expired": int(expired),
        "items": [
            {
                "id": str(item.id),
                "challenge_type": item.challenge_type,
                "status": item.status,
                "response_received": item.response_received,
                "response_valid": item.response_valid,
                "verification_result": item.verification_result,
                "issued_at": item.issued_at.isoformat(),
                "responded_at": item.responded_at.isoformat() if item.responded_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            }
            for item in items
        ],
    }
