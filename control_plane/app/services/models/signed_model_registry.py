from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.admin_action_log import AdminActionLog
from app.models.client import Client
from app.models.commercial_model_supply_chain import (
    CommercialModelProvenanceAttestation,
    CommercialModelRevocationRecord,
    CommercialSignedModelRegistryEntry,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from fastapi import HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

LOCAL_MODEL_FORMATS = {"gguf", "safetensors", "onnx"}
TRUSTED_STATES = {"trusted"}
BLOCKED_STATES = {"untrusted", "quarantined", "revoked"}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sign_secret() -> str:
    settings = get_settings()
    return (
        settings.commercial_governance_federation_shared_token
        or settings.commercial_tenant_encryption_master_key
        or settings.admin_token
    )


def _manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_name": payload.get("model_name"),
        "model_alias": payload.get("model_alias"),
        "model_version": payload.get("model_version"),
        "provider": payload.get("provider"),
        "model_file_path": payload.get("model_file_path"),
        "model_format": payload.get("model_format"),
        "checksum_sha256": payload.get("checksum_sha256"),
        "provenance_id": payload.get("provenance_id"),
        "tenant_scope_json": payload.get("tenant_scope_json"),
    }


def _sanitize_path_like(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = sanitize_report_payload({"value": value}).get("value")
    if not isinstance(sanitized, str):
        return None
    return sanitized.replace("\n", " ").replace("\r", " ")[:512]


def _sanitize_text(value: str | None, *, max_length: int = 255) -> str | None:
    if value is None:
        return None
    sanitized = sanitize_report_payload({"value": value}).get("value")
    if sanitized is None:
        return None
    return str(sanitized).replace("\n", " ").replace("\r", " ")[:max_length]


def _matches_tenant_scope(scope: dict[str, Any] | None, client: Client | None) -> bool:
    if not scope or client is None:
        return True
    client_ids = {str(item) for item in (scope.get("client_ids") or [])}
    client_names = {str(item) for item in (scope.get("client_names") or [])}
    billing_plan_codes = {str(item) for item in (scope.get("billing_plan_codes") or [])}
    if client_ids and str(client.id) not in client_ids:
        return False
    if client_names and client.name not in client_names:
        return False
    if billing_plan_codes and getattr(client.billing_plan, "code", None) not in billing_plan_codes:
        return False
    return True


async def _log_audit(
    db: AsyncSession,
    *,
    action: str,
    status: str,
    payload: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminActionLog(
            action=action,
            admin_role="super_admin",
            payload_json=sanitize_report_payload(payload or {}),
            result_json=sanitize_report_payload(result or {}),
            status=status,
        )
    )
    await db.flush()


async def calculate_model_checksum(model_file_path: str) -> str:
    path = Path(model_file_path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def sign_model_manifest(manifest: dict[str, Any]) -> str:
    return hmac.new(
        _sign_secret().encode("utf-8"),
        _canonical_json(manifest).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def verify_model_signature(manifest: dict[str, Any], signature: str | None) -> bool:
    if not signature:
        return False
    expected = await sign_model_manifest(manifest)
    return hmac.compare_digest(signature, expected)


async def register_model_manifest(
    db: AsyncSession,
    *,
    model_name: str,
    model_alias: str | None = None,
    model_version: str | None = None,
    provider: str | None = None,
    model_file_path: str | None = None,
    model_format: str,
    checksum_sha256: str | None = None,
    signature: str | None = None,
    provenance_id: UUID | None = None,
    tenant_scope_json: dict[str, Any] | None = None,
    trust_state: str | None = None,
) -> CommercialSignedModelRegistryEntry:
    settings = get_settings()
    sanitized_scope = sanitize_report_payload(tenant_scope_json) if tenant_scope_json is not None else None
    sanitized_path = _sanitize_path_like(model_file_path)
    model_format = _sanitize_text(model_format, max_length=32) or "other"
    is_local_artifact = model_format in LOCAL_MODEL_FORMATS

    if is_local_artifact and settings.commercial_model_require_checksum_for_local:
        if not sanitized_path:
            raise ValueError("Local model registration requires model_file_path")
        if not checksum_sha256:
            checksum_sha256 = await calculate_model_checksum(sanitized_path)

    if not checksum_sha256:
        checksum_sha256 = "manifest-only"

    manifest = _manifest_payload(
        {
            "model_name": _sanitize_text(model_name),
            "model_alias": _sanitize_text(model_alias, max_length=128),
            "model_version": _sanitize_text(model_version, max_length=128),
            "provider": _sanitize_text(provider, max_length=128),
            "model_file_path": sanitized_path,
            "model_format": model_format,
            "checksum_sha256": checksum_sha256,
            "provenance_id": str(provenance_id) if provenance_id else None,
            "tenant_scope_json": sanitized_scope,
        }
    )
    manifest_hash = hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
    if signature and not await verify_model_signature(manifest, signature):
        raise ValueError("Invalid model manifest signature")

    entry = CommercialSignedModelRegistryEntry(
        model_name=manifest["model_name"] or "",
        model_alias=manifest["model_alias"],
        model_version=manifest["model_version"],
        provider=manifest["provider"],
        model_file_path=manifest["model_file_path"],
        model_format=model_format,
        checksum_sha256=checksum_sha256,
        manifest_hash=manifest_hash,
        signature=signature,
        provenance_id=provenance_id,
        trust_state=trust_state or ("pending" if provenance_id or signature else "untrusted"),
        tenant_scope_json=sanitized_scope,
    )
    db.add(entry)
    await db.flush()
    await _log_audit(
        db,
        action="model_registered",
        status="success",
        payload={"model_name": entry.model_name, "model_alias": entry.model_alias, "model_format": entry.model_format},
        result={"registry_entry_id": str(entry.id), "trust_state": entry.trust_state, "manifest_hash": entry.manifest_hash},
    )
    return entry


async def verify_model_checksum(
    db: AsyncSession,
    entry: CommercialSignedModelRegistryEntry,
) -> dict[str, Any]:
    if not entry.model_file_path:
        result = {"verified": entry.model_format == "api", "reason": "manifest_only"}
        await _log_audit(
            db,
            action="checksum_verified",
            status="success" if result["verified"] else "skipped",
            payload={"registry_entry_id": str(entry.id)},
            result=result,
        )
        return result

    actual = await calculate_model_checksum(entry.model_file_path)
    if actual != entry.checksum_sha256:
        settings = get_settings()
        if settings.commercial_model_quarantine_on_checksum_mismatch:
            entry.trust_state = "quarantined"
        entry.updated_at = utc_now()
        await _log_audit(
            db,
            action="checksum_mismatch",
            status="failure",
            payload={"registry_entry_id": str(entry.id), "model_name": entry.model_name},
            result={"expected": entry.checksum_sha256, "actual": actual, "trust_state": entry.trust_state},
        )
        return {"verified": False, "reason": "checksum_mismatch", "expected": entry.checksum_sha256, "actual": actual}

    await _log_audit(
        db,
        action="checksum_verified",
        status="success",
        payload={"registry_entry_id": str(entry.id), "model_name": entry.model_name},
        result={"checksum": actual},
    )
    return {"verified": True, "checksum": actual, "reason": "checksum_ok"}


async def approve_model(
    db: AsyncSession,
    entry_id: UUID,
    *,
    approved_by: str | None,
) -> CommercialSignedModelRegistryEntry:
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id)
    if not entry:
        raise ValueError("Registry entry not found")
    entry.trust_state = "trusted"
    entry.approved_by = _sanitize_text(approved_by)
    entry.approved_at = utc_now()
    entry.updated_at = utc_now()
    await _log_audit(
        db,
        action="model_approved",
        status="success",
        payload={"registry_entry_id": str(entry.id), "model_name": entry.model_name},
        result={"trust_state": entry.trust_state, "approved_by": entry.approved_by},
    )
    await db.flush()
    return entry


async def quarantine_model(
    db: AsyncSession,
    entry_id: UUID,
    *,
    reason: str,
    revoked_by: str | None = None,
) -> CommercialSignedModelRegistryEntry:
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id)
    if not entry:
        raise ValueError("Registry entry not found")
    entry.trust_state = "quarantined"
    entry.updated_at = utc_now()
    db.add(
        CommercialModelRevocationRecord(
            registry_entry_id=entry.id,
            model_name=entry.model_name,
            reason=_sanitize_text(reason, max_length=1000) or "manual quarantine",
            revocation_type="manual",
            revoked_by=_sanitize_text(revoked_by),
        )
    )
    await _log_audit(
        db,
        action="model_quarantined",
        status="success",
        payload={"registry_entry_id": str(entry.id), "model_name": entry.model_name},
        result={"reason": reason},
    )
    await db.flush()
    return entry


async def revoke_model(
    db: AsyncSession,
    *,
    entry_id: UUID | None = None,
    model_name: str | None = None,
    reason: str,
    revocation_type: str,
    revoked_by: str | None = None,
) -> CommercialModelRevocationRecord:
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id) if entry_id else None
    resolved_name = model_name or (entry.model_name if entry else None)
    if not resolved_name:
        raise ValueError("model_name or entry_id is required")
    if entry is not None:
        entry.trust_state = "revoked"
        entry.updated_at = utc_now()
    record = CommercialModelRevocationRecord(
        registry_entry_id=entry.id if entry else None,
        model_name=resolved_name,
        reason=_sanitize_text(reason, max_length=1000) or "revoked",
        revocation_type=revocation_type,
        revoked_by=_sanitize_text(revoked_by),
    )
    db.add(record)
    await db.flush()
    await _log_audit(
        db,
        action="model_revoked",
        status="success",
        payload={"registry_entry_id": str(entry.id) if entry else None, "model_name": resolved_name},
        result={"revocation_type": revocation_type},
    )
    return record


async def _latest_entry_for_model(
    db: AsyncSession,
    model_name: str,
) -> CommercialSignedModelRegistryEntry | None:
    result = await db.execute(
        select(CommercialSignedModelRegistryEntry)
        .where(
            or_(
                CommercialSignedModelRegistryEntry.model_name == model_name,
                CommercialSignedModelRegistryEntry.model_alias == model_name,
            )
        )
        .order_by(desc(CommercialSignedModelRegistryEntry.updated_at), desc(CommercialSignedModelRegistryEntry.created_at))
    )
    return result.scalars().first()


async def get_model_trust_state(
    db: AsyncSession,
    model_name: str,
    *,
    client: Client | None = None,
) -> dict[str, Any]:
    entry = await _latest_entry_for_model(db, model_name)
    if entry is None:
        return {
            "registry_entry_id": None,
            "trust_state": "untrusted",
            "allowed": False,
            "reason": "not_registered",
            "manifest_hash": None,
            "checksum_sha256": None,
        }
    if not _matches_tenant_scope(entry.tenant_scope_json, client):
        return {
            "registry_entry_id": str(entry.id),
            "trust_state": "untrusted",
            "allowed": False,
            "reason": "tenant_scope_mismatch",
            "manifest_hash": entry.manifest_hash,
            "checksum_sha256": entry.checksum_sha256,
        }
    allowed = entry.trust_state in TRUSTED_STATES
    return {
        "registry_entry_id": str(entry.id),
        "trust_state": entry.trust_state,
        "allowed": allowed,
        "reason": "ok" if allowed else f"trust_state_{entry.trust_state}",
        "manifest_hash": entry.manifest_hash,
        "checksum_sha256": entry.checksum_sha256,
        "provenance_id": str(entry.provenance_id) if entry.provenance_id else None,
        "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        "approved_by": entry.approved_by,
        "tenant_scope_json": entry.tenant_scope_json,
    }


async def list_trusted_models(
    db: AsyncSession,
    *,
    client: Client | None = None,
) -> list[CommercialSignedModelRegistryEntry]:
    result = await db.execute(
        select(CommercialSignedModelRegistryEntry)
        .where(CommercialSignedModelRegistryEntry.trust_state == "trusted")
        .order_by(desc(CommercialSignedModelRegistryEntry.updated_at))
    )
    entries = result.scalars().all()
    return [entry for entry in entries if _matches_tenant_scope(entry.tenant_scope_json, client)]


async def enforce_model_trust_or_warn(
    db: AsyncSession,
    *,
    model_name: str,
    client: Client | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.commercial_model_supply_chain_enabled:
        return {"allowed": True, "mode": "disabled", "trust_state": "disabled"}

    trust = await get_model_trust_state(db, model_name, client=client)
    mode = settings.commercial_model_trust_enforcement_mode
    trust["mode"] = mode
    if mode == "disabled":
        trust["allowed"] = True
        return trust
    if mode == "report_only":
        return trust | {"allowed": True, "warning": None if trust["trust_state"] == "trusted" else trust["reason"]}
    if trust["trust_state"] != "trusted":
        raise HTTPException(status_code=403, detail={"error": "model_not_trusted", **trust})
    return trust


async def latest_registry_map(db: AsyncSession) -> dict[str, CommercialSignedModelRegistryEntry]:
    result = await db.execute(
        select(CommercialSignedModelRegistryEntry).order_by(
            CommercialSignedModelRegistryEntry.model_name.asc(),
            CommercialSignedModelRegistryEntry.updated_at.desc(),
            CommercialSignedModelRegistryEntry.created_at.desc(),
        )
    )
    mapping: dict[str, CommercialSignedModelRegistryEntry] = {}
    for entry in result.scalars().all():
        mapping.setdefault(entry.model_name, entry)
        if entry.model_alias:
            mapping.setdefault(entry.model_alias, entry)
    return mapping


async def get_provenance_entry(
    db: AsyncSession,
    provenance_id: UUID | None,
) -> CommercialModelProvenanceAttestation | None:
    if provenance_id is None:
        return None
    return await db.get(CommercialModelProvenanceAttestation, provenance_id)
