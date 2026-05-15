from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_attestation_runtime import (
    CommercialAttestationChallenge,
    CommercialAttestationEvidence,
    CommercialAttestationPolicy,
    CommercialRuntimeAttestation,
    CommercialRuntimeMeasurement,
)
from app.services.routing.commercial_report_export import sanitize_report_payload


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_payload(payload: dict[str, Any]) -> str:
    return _hash_bytes(_canonical_json(payload).encode("utf-8"))


def _runtime_fingerprint() -> dict[str, Any]:
    import platform
    import os
    return {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "pid": os.getpid(),
    }


def _compute_immutable_hash(payload: dict[str, Any], previous_hash: str | None = None) -> str:
    raw = _canonical_json(payload)
    if previous_hash:
        raw = previous_hash + raw
    return _hash_bytes(raw.encode("utf-8"))


def _enclave_type_from_settings() -> str:
    return get_settings().commercial_runtime_attestation_enclave_type


def _platform_type_from_settings() -> str:
    return get_settings().commercial_runtime_attestation_platform_type


def _attestation_mode_from_settings() -> str:
    return get_settings().commercial_runtime_attestation_mode


# --- Enclave Placeholders ---

def tpm_placeholder() -> dict[str, Any]:
    return {
        "enclave": "tpm_placeholder",
        "boot_measurement": "tpm_pcr_placeholder_sha256",
        "boot_healthy": True,
        "tpm_version": "2.0_placeholder",
        "tpm_manufacturer": "placeholder",
    }


def sev_placeholder() -> dict[str, Any]:
    return {
        "enclave": "sev_placeholder",
        "platform": "amd_sev_snp_placeholder",
        "policy": "sev_es_policy_placeholder",
        "chip_id": "sev_chip_id_placeholder",
        "build": "sev_build_placeholder",
    }


def sgx_placeholder() -> dict[str, Any]:
    return {
        "enclave": "sgx_placeholder",
        "mr_enclave": "sgx_mr_enclave_placeholder",
        "mr_signer": "sgx_mr_signer_placeholder",
        "prod": True,
        "debug": False,
    }


def vbs_placeholder() -> dict[str, Any]:
    return {
        "enclave": "vbs_placeholder",
        "vbs_version": "hyperv_vbs_placeholder",
        "secure_kernel": True,
        "memory_isolation": "virtual_based_security_placeholder",
    }


def software_attested() -> dict[str, Any]:
    fp = _runtime_fingerprint()
    return {
        "enclave": "software_attested",
        "fingerprint": fp,
        "runtime_type": "software_attested_placeholder",
    }


def collect_enclave_evidence(enclave_type: str | None = None) -> dict[str, Any]:
    enclave = enclave_type or _enclave_type_from_settings()
    collectors = {
        "tpm_placeholder": tpm_placeholder,
        "sev_placeholder": sev_placeholder,
        "sgx_placeholder": sgx_placeholder,
        "vbs_placeholder": vbs_placeholder,
        "software_attested": software_attested,
    }
    collector = collectors.get(enclave, software_attested)
    return collector()


# --- Runtime Attestation Core ---

def _build_attestation_evidence(
    runtime_hash: str,
    model_hash: str | None,
    workflow_hash: str | None,
    policy_hash: str | None,
    enclave_evidence: dict[str, Any],
) -> dict[str, Any]:
    fp = _runtime_fingerprint()
    return sanitize_report_payload({
        "runtime_hash": runtime_hash,
        "model_hash": model_hash,
        "workflow_hash": workflow_hash,
        "policy_hash": policy_hash,
        "enclave_evidence": enclave_evidence,
        "runtime_fingerprint": fp,
    })


def _build_attestation_measurement(
    model_hash: str | None = None,
    workflow_hash: str | None = None,
    policy_hash: str | None = None,
    routing_hash: str | None = None,
    runtime_binary_hash: str | None = None,
) -> dict[str, Any]:
    return sanitize_report_payload({
        "loaded_model_hashes": [model_hash] if model_hash else [],
        "workflow_hashes": [workflow_hash] if workflow_hash else [],
        "policy_bundle_hashes": [policy_hash] if policy_hash else [],
        "routing_hashes": [routing_hash] if routing_hash else [],
        "runtime_binary_hashes": [runtime_binary_hash] if runtime_binary_hash else [],
    })


async def create_runtime_attestation(
    db: AsyncSession,
    *,
    cluster_id: str,
    node_id: str | None = None,
    tenant_id: str | None = None,
    runtime_hash: str | None = None,
    firmware_hash: str | None = None,
    model_hash: str | None = None,
    workflow_hash: str | None = None,
    policy_hash: str | None = None,
    enclave_type: str | None = None,
    platform_type: str | None = None,
    previous_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeAttestation:
    settings = get_settings()
    enclave = enclave_type or _enclave_type_from_settings()
    platform = platform_type or _platform_type_from_settings()

    runtime_hash = runtime_hash or _hash_payload(_runtime_fingerprint())

    enclave_evidence = collect_enclave_evidence(enclave)
    evidence = _build_attestation_evidence(
        runtime_hash=runtime_hash,
        model_hash=model_hash,
        workflow_hash=workflow_hash,
        policy_hash=policy_hash,
        enclave_evidence=enclave_evidence,
    )
    evidence_hash = _hash_payload(evidence)

    measurement = _build_attestation_measurement(
        model_hash=model_hash,
        workflow_hash=workflow_hash,
        policy_hash=policy_hash,
    )

    previous_hash: str | None = None
    if previous_attestation_id:
        prev = await db.get(CommercialRuntimeAttestation, previous_attestation_id)
        if prev:
            previous_hash = prev.immutable_hash

    chain_data = {
        "runtime_hash": runtime_hash,
        "evidence_hash": evidence_hash,
        "enclave": enclave,
        "timestamp": utc_now().isoformat(),
    }
    immutable_hash = _compute_immutable_hash(chain_data, previous_hash=previous_hash)

    record = CommercialRuntimeAttestation(
        node_id=node_id,
        cluster_id=cluster_id,
        tenant_id=tenant_id,
        runtime_hash=runtime_hash,
        firmware_hash=firmware_hash,
        model_hash=model_hash,
        workflow_hash=workflow_hash,
        policy_hash=policy_hash,
        evidence_hash=evidence_hash,
        trust_score=0.0,
        attestation_mode=_attestation_mode_from_settings(),
        enclave_type=enclave,
        platform_type=platform,
        immutable_hash=immutable_hash,
        previous_hash=previous_hash,
        status="pending",
        drift_detected=False,
        drift_score=0.0,
        trusted=False,
        evidence_json=evidence,
        measurement_json=measurement,
        metadata_json={},
        attested_at=utc_now(),
        expires_at=utc_now() + timedelta(seconds=settings.commercial_runtime_attestation_evidence_ttl_seconds),
    )
    db.add(record)
    await db.flush()
    return record


async def verify_runtime_attestation(
    db: AsyncSession,
    attestation_id: uuid.UUID,
) -> CommercialRuntimeAttestation:
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise ValueError("Attestation record not found")

    if record.expires_at and record.expires_at < utc_now():
        record.status = "expired"
        record.trusted = False
        record.verified_at = utc_now()
        await db.flush()
        return record

    if record.revoked_at:
        record.status = "revoked"
        record.trusted = False
        record.verified_at = utc_now()
        await db.flush()
        return record

    expected_evidence_hash = _hash_payload(record.evidence_json)
    if expected_evidence_hash != record.evidence_hash:
        record.status = "untrusted"
        record.trusted = False
        record.drift_detected = True
        record.verified_at = utc_now()
        await db.flush()
        return record

    record.status = "trusted"
    record.trusted = True
    record.verified_at = utc_now()
    await db.flush()
    return record


async def compute_trust_score(
    db: AsyncSession,
    attestation_id: uuid.UUID,
) -> float:
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise ValueError("Attestation record not found")

    score = 1.0

    if record.status == "expired":
        score -= 0.3
    if record.status == "revoked":
        score -= 0.5
    if record.status == "untrusted":
        score -= 0.4
    if record.drift_detected:
        score -= record.drift_score
    if record.enclave_type == "software_attested":
        score -= 0.2
    if record.enclave_type in ("tpm_placeholder", "sev_placeholder", "sgx_placeholder", "vbs_placeholder"):
        score += 0.1
    if record.measurement_chain_hash:
        score += 0.1

    score = max(0.0, min(1.0, score))
    record.trust_score = score
    await db.flush()
    return score


async def detect_drift(
    db: AsyncSession,
    attestation_id: uuid.UUID,
    *,
    runtime_hash: str | None = None,
    model_hash: str | None = None,
    workflow_hash: str | None = None,
) -> dict[str, Any]:
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise ValueError("Attestation record not found")

    drift_reasons: list[str] = []
    drift_count = 0

    if runtime_hash and runtime_hash != record.runtime_hash:
        drift_reasons.append("runtime_hash_changed")
        drift_count += 1
    if model_hash and model_hash != record.model_hash:
        drift_reasons.append("model_hash_changed")
        drift_count += 1
    if workflow_hash and workflow_hash != record.workflow_hash:
        drift_reasons.append("workflow_hash_changed")
        drift_count += 1

    if record.expires_at and record.expires_at < utc_now():
        drift_reasons.append("attestation_expired")
        drift_count += 1

    drift_score = drift_count / 5.0
    drift_score = min(1.0, drift_score)

    record.drift_detected = len(drift_reasons) > 0
    record.drift_score = drift_score
    if record.drift_detected:
        record.status = "drift"
        record.trusted = False
    await db.flush()

    return {
        "drift_detected": record.drift_detected,
        "drift_score": drift_score,
        "drift_reasons": drift_reasons,
    }


async def attestation_chaining(
    db: AsyncSession,
    attestation_id: uuid.UUID,
    evidence_ids: list[uuid.UUID] | None = None,
) -> str:
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise ValueError("Attestation record not found")

    if not evidence_ids:
        result = await db.execute(
            select(CommercialAttestationEvidence)
            .where(CommercialAttestationEvidence.runtime_attestation_id == attestation_id)
            .order_by(CommercialAttestationEvidence.chain_position)
        )
        evidence_records = result.scalars().all()
        evidence_ids = [e.id for e in evidence_records]

    chain_parts: list[str] = [record.immutable_hash]
    for ev_id in evidence_ids:
        ev = await db.get(CommercialAttestationEvidence, ev_id)
        if ev:
            chain_parts.append(ev.evidence_hash)

    chain_hash = _hash_bytes(":".join(chain_parts).encode("utf-8"))
    record.measurement_chain_hash = chain_hash
    await db.flush()
    return chain_hash


async def revoke_attestation(
    db: AsyncSession,
    attestation_id: uuid.UUID,
    reason: str | None = None,
) -> CommercialRuntimeAttestation:
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise ValueError("Attestation record not found")
    record.status = "revoked"
    record.trusted = False
    record.revoked_at = utc_now()
    if reason:
        record.metadata_json["revocation_reason"] = reason
    await db.flush()
    return record


async def summarize_attestation_status(db: AsyncSession) -> dict[str, Any]:
    total = (await db.execute(select(func.count(CommercialRuntimeAttestation.id)))).scalar() or 0
    trusted = (await db.execute(
        select(func.count(CommercialRuntimeAttestation.id))
        .where(CommercialRuntimeAttestation.trusted.is_(True))
    )).scalar() or 0
    drift_count = (await db.execute(
        select(func.count(CommercialRuntimeAttestation.id))
        .where(CommercialRuntimeAttestation.drift_detected.is_(True))
    )).scalar() or 0
    untrusted_count = (await db.execute(
        select(func.count(CommercialRuntimeAttestation.id))
        .where(CommercialRuntimeAttestation.status == "untrusted")
    )).scalar() or 0
    expired_count = (await db.execute(
        select(func.count(CommercialRuntimeAttestation.id))
        .where(CommercialRuntimeAttestation.status == "expired")
    )).scalar() or 0
    revoked_count = (await db.execute(
        select(func.count(CommercialRuntimeAttestation.id))
        .where(CommercialRuntimeAttestation.status == "revoked")
    )).scalar() or 0

    recent = await db.execute(
        select(CommercialRuntimeAttestation)
        .order_by(CommercialRuntimeAttestation.created_at.desc())
        .limit(20)
    )
    items = recent.scalars().all()

    avg_trust = await db.execute(
        select(func.avg(CommercialRuntimeAttestation.trust_score))
    )
    avg_trust_score = float(avg_trust.scalar() or 0.0)

    return {
        "total_attestations": int(total),
        "trusted_count": int(trusted),
        "drift_count": int(drift_count),
        "untrusted_count": int(untrusted_count),
        "expired_count": int(expired_count),
        "revoked_count": int(revoked_count),
        "avg_trust_score": round(avg_trust_score, 4),
        "items": [
            {
                "id": str(item.id),
                "node_id": item.node_id,
                "cluster_id": item.cluster_id,
                "status": item.status,
                "trusted": item.trusted,
                "trust_score": item.trust_score,
                "drift_detected": item.drift_detected,
                "drift_score": item.drift_score,
                "attestation_mode": item.attestation_mode,
                "enclave_type": item.enclave_type,
                "attested_at": item.attested_at.isoformat(),
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            }
            for item in items
        ],
    }
