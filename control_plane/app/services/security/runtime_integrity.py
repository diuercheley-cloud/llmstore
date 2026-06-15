from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_attestation_runtime import (
    CommercialAttestationPolicy,
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


async def create_attestation_policy(
    db: AsyncSession,
    *,
    policy_name: str,
    policy_version: str = "1.0",
    min_trust_score: float = 0.0,
    max_drift_threshold: float = 0.1,
    require_signed_evidence: bool = False,
    require_measurement_chain: bool = False,
    require_model_binding: bool = False,
    require_workflow_binding: bool = False,
    allowed_enclave_types: list[str] | None = None,
    allowed_platform_types: list[str] | None = None,
    enforcement_mode: str = "report_only",
    block_untrusted: bool = False,
    require_for_sovereign: bool = False,
    require_for_sensitive_tenants: bool = False,
) -> CommercialAttestationPolicy:
    policy_data = sanitize_report_payload(
        {
            "policy_name": policy_name,
            "policy_version": policy_version,
            "min_trust_score": min_trust_score,
            "max_drift_threshold": max_drift_threshold,
            "require_signed_evidence": require_signed_evidence,
            "require_measurement_chain": require_measurement_chain,
            "require_model_binding": require_model_binding,
            "require_workflow_binding": require_workflow_binding,
            "allowed_enclave_types": allowed_enclave_types or [],
            "allowed_platform_types": allowed_platform_types or [],
            "enforcement_mode": enforcement_mode,
            "block_untrusted": block_untrusted,
            "require_for_sovereign": require_for_sovereign,
            "require_for_sensitive_tenants": require_for_sensitive_tenants,
        }
    )
    policy_hash = _hash_payload(policy_data)

    record = CommercialAttestationPolicy(
        policy_name=policy_name,
        policy_hash=policy_hash,
        policy_version=policy_version,
        min_trust_score=min_trust_score,
        max_drift_threshold=max_drift_threshold,
        require_signed_evidence=require_signed_evidence,
        require_measurement_chain=require_measurement_chain,
        require_model_binding=require_model_binding,
        require_workflow_binding=require_workflow_binding,
        allowed_enclave_types_json=allowed_enclave_types or [],
        allowed_platform_types_json=allowed_platform_types or [],
        enforcement_mode=enforcement_mode,
        block_untrusted=block_untrusted,
        require_for_sovereign=require_for_sovereign,
        require_for_sensitive_tenants=require_for_sensitive_tenants,
        is_active=True,
        metadata_json={},
    )
    db.add(record)
    await db.flush()
    return record


async def evaluate_attestation_against_policy(
    db: AsyncSession,
    attestation_id: uuid.UUID,
    policy_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    attestation = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not attestation:
        raise ValueError("Attestation record not found")

    if policy_id:
        policy = await db.get(CommercialAttestationPolicy, policy_id)
    else:
        result = await db.execute(
            select(CommercialAttestationPolicy)
            .where(CommercialAttestationPolicy.is_active.is_(True))
            .order_by(CommercialAttestationPolicy.created_at.desc())
            .limit(1)
        )
        policy = result.scalars().first()

    if not policy:
        return {
            "passed": True,
            "policy_name": None,
            "reasons": ["no_active_policy"],
            "enforcement": "report_only",
        }

    reasons: list[str] = []
    if attestation.trust_score < policy.min_trust_score:
        reasons.append(
            f"trust_score_below_minimum: {attestation.trust_score} < {policy.min_trust_score}"
        )
    if attestation.drift_score > policy.max_drift_threshold:
        reasons.append(
            f"drift_score_above_threshold: {attestation.drift_score} > {policy.max_drift_threshold}"
        )
    if policy.allowed_enclave_types_json:
        if attestation.enclave_type not in policy.allowed_enclave_types_json:
            reasons.append(f"enclave_type_not_allowed: {attestation.enclave_type}")
    if policy.allowed_platform_types_json:
        if attestation.platform_type not in policy.allowed_platform_types_json:
            reasons.append(f"platform_type_not_allowed: {attestation.platform_type}")
    if policy.require_model_binding and not attestation.model_hash:
        reasons.append("model_binding_required_but_not_provided")
    if policy.require_workflow_binding and not attestation.workflow_hash:
        reasons.append("workflow_binding_required_but_not_provided")
    if policy.require_measurement_chain and not attestation.measurement_chain_hash:
        reasons.append("measurement_chain_required_but_not_provided")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "policy_name": policy.policy_name,
        "policy_hash": policy.policy_hash,
        "reasons": reasons,
        "enforcement": policy.enforcement_mode,
        "block_untrusted": policy.block_untrusted,
    }


async def block_untrusted_runtimes(
    db: AsyncSession,
    *,
    cluster_id: str,
    tenant_id: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    effective_mode = mode or settings.commercial_runtime_attestation_mode

    query = select(CommercialRuntimeAttestation).where(
        CommercialRuntimeAttestation.cluster_id == cluster_id,
    )
    if tenant_id:
        query = query.where(CommercialRuntimeAttestation.tenant_id == tenant_id)
    query = query.order_by(CommercialRuntimeAttestation.created_at.desc()).limit(10)

    result = await db.execute(query)
    records = result.scalars().all()

    if not records:
        if effective_mode == "enforce":
            raise ValueError("No attestation records available for enforce mode")
        return {"allowed": effective_mode != "disabled", "status": "unknown", "records": 0}

    untrusted = [
        r
        for r in records
        if not r.trusted or r.status in ("untrusted", "drift", "expired", "revoked")
    ]
    if untrusted and effective_mode == "enforce":
        raise ValueError(
            f"Runtime attestation enforcement blocked: {len(untrusted)} untrusted runtime(s) present"
        )

    return {
        "allowed": len(untrusted) == 0 or effective_mode != "enforce",
        "total_records": len(records),
        "untrusted_count": len(untrusted),
        "status": "trusted" if len(untrusted) == 0 else "untrusted",
    }


async def require_attestation_for_sensitive_tenants(
    db: AsyncSession,
    *,
    tenant_id: str,
    cluster_id: str,
    mode: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.commercial_runtime_attestation_require_for_sensitive_tenants:
        return {"required": False, "reason": "feature_disabled"}

    effective_mode = mode or settings.commercial_runtime_attestation_mode

    result = await db.execute(
        select(CommercialRuntimeAttestation)
        .where(
            CommercialRuntimeAttestation.tenant_id == tenant_id,
            CommercialRuntimeAttestation.cluster_id == cluster_id,
            CommercialRuntimeAttestation.trusted.is_(True),
        )
        .order_by(CommercialRuntimeAttestation.created_at.desc())
        .limit(1)
    )
    attestation = result.scalars().first()

    if not attestation:
        if effective_mode == "enforce":
            raise ValueError(f"No trusted attestation for sensitive tenant {tenant_id}")
        return {"required": True, "compliant": False, "reason": "no_trusted_attestation"}

    return {
        "required": True,
        "compliant": attestation.trusted,
        "trust_score": attestation.trust_score,
        "attestation_id": str(attestation.id),
    }


async def require_attestation_for_sovereign(
    db: AsyncSession,
    *,
    cluster_id: str,
    mode: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.commercial_runtime_attestation_require_for_sovereign:
        return {"required": False, "reason": "feature_disabled"}

    effective_mode = mode or settings.commercial_runtime_attestation_mode

    result = await db.execute(
        select(CommercialRuntimeAttestation)
        .where(
            CommercialRuntimeAttestation.cluster_id == cluster_id,
            CommercialRuntimeAttestation.trusted.is_(True),
        )
        .order_by(CommercialRuntimeAttestation.created_at.desc())
        .limit(1)
    )
    attestation = result.scalars().first()

    if not attestation:
        if effective_mode == "enforce":
            raise ValueError(
                f"No trusted attestation for sovereign runtime in cluster {cluster_id}"
            )
        return {"required": True, "compliant": False, "reason": "no_trusted_attestation"}

    return {
        "required": True,
        "compliant": attestation.trusted,
        "trust_score": attestation.trust_score,
        "attestation_id": str(attestation.id),
    }


async def measure_loaded_models_integrity(
    db: AsyncSession,
    *,
    cluster_id: str,
    model_hashes: list[dict[str, str]],
    attestation_id: uuid.UUID,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    attestation = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not attestation:
        raise ValueError("Attestation not found")

    for mh in model_hashes:
        model_id = mh.get("model_id", "unknown")
        expected_hash = mh.get("expected_hash")
        observed_hash = mh.get("observed_hash")
        drift = expected_hash and observed_hash and expected_hash != observed_hash
        results.append(
            {
                "model_id": model_id,
                "expected_hash": expected_hash,
                "observed_hash": observed_hash,
                "drift_detected": bool(drift),
            }
        )

    any_drift = any(r["drift_detected"] for r in results)
    if any_drift:
        attestation.drift_detected = True
        attestation.drift_score = sum(1 for r in results if r["drift_detected"]) / max(
            len(results), 1
        )
        attestation.status = "drift"
        attestation.trusted = False
        await db.flush()

    return results


async def verify_inference_adapter_integrity(
    db: AsyncSession,
    *,
    cluster_id: str,
    adapter_name: str,
    expected_hash: str,
    observed_hash: str | None = None,
) -> dict[str, Any]:
    drift_detected = observed_hash is not None and expected_hash != observed_hash
    return {
        "adapter_name": adapter_name,
        "expected_hash": expected_hash,
        "observed_hash": observed_hash or "not_available",
        "drift_detected": drift_detected,
        "status": "drift" if drift_detected else "valid",
    }


async def summarize_integrity_status(db: AsyncSession) -> dict[str, Any]:
    total_attestations = (
        await db.execute(select(func.count(CommercialRuntimeAttestation.id)))
    ).scalar() or 0
    trusted_count = (
        await db.execute(
            select(func.count(CommercialRuntimeAttestation.id)).where(
                CommercialRuntimeAttestation.trusted.is_(True)
            )
        )
    ).scalar() or 0
    drift_count = (
        await db.execute(
            select(func.count(CommercialRuntimeAttestation.id)).where(
                CommercialRuntimeAttestation.drift_detected.is_(True)
            )
        )
    ).scalar() or 0

    policy_count = (
        await db.execute(
            select(func.count(CommercialAttestationPolicy.id)).where(
                CommercialAttestationPolicy.is_active.is_(True)
            )
        )
    ).scalar() or 0

    return {
        "total_attestations": int(total_attestations),
        "trusted_runtimes": int(trusted_count),
        "drift_detected": int(drift_count),
        "active_policies": int(policy_count),
        "sovereign_restricted_attested": True,
    }
