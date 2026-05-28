from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.commercial_model_supply_chain import (
    CommercialRuntimeModelAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.models.model_registry import ModelRegistry
from app.services.models.signed_model_registry import calculate_model_checksum
from app.services.routing.commercial_report_export import sanitize_report_payload


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _safe_runtime_path(model: ModelRegistry, settings: Settings | None = None) -> str | None:
    cfg = settings or get_settings()
    model_file = (model.model_file or "").strip()
    if not model_file:
        return None
    candidate = Path(model_file)
    if candidate.is_absolute():
        return str(candidate)
    return str((Path(cfg.models_dir) / model_file).resolve())


def _build_runtime_manifest(
    model: ModelRegistry,
    *,
    entry: CommercialSignedModelRegistryEntry | None = None,
    observed_checksum: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime_path = _safe_runtime_path(model, settings=settings)
    return {
        "model_name": entry.model_name if entry else model.model_id,
        "model_alias": model.model_alias if model.model_alias is not None else (entry.model_alias if entry else None),
        "model_version": entry.model_version if entry else None,
        "provider": entry.provider if entry else model.provider,
        "model_file_path": runtime_path or (entry.model_file_path if entry else None),
        "model_format": entry.model_format if entry else "other",
        "checksum_sha256": observed_checksum or (entry.checksum_sha256 if entry else None),
        "provenance_id": str(entry.provenance_id) if entry and entry.provenance_id else None,
        "tenant_scope_json": entry.tenant_scope_json if entry else None,
    }


def _hash_manifest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


async def compare_runtime_vs_registry(
    model: ModelRegistry,
    entry: CommercialSignedModelRegistryEntry | None,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime_path = _safe_runtime_path(model, settings=settings)
    observed_checksum: str | None = None
    if runtime_path and Path(runtime_path).exists():
        observed_checksum = await calculate_model_checksum(runtime_path)
    runtime_manifest = _build_runtime_manifest(
        model,
        entry=entry,
        observed_checksum=observed_checksum or (entry.checksum_sha256 if entry and entry.checksum_sha256 == "manifest-only" else None),
        settings=settings,
    )

    expected_manifest_hash = entry.manifest_hash if entry else None
    observed_manifest_hash = _hash_manifest(runtime_manifest)
    expected_checksum = entry.checksum_sha256 if entry else None

    drift_reasons: list[str] = []
    if entry is None:
        drift_reasons.append("not_registered")
    if entry and entry.model_alias and model.model_alias and entry.model_alias != model.model_alias:
        drift_reasons.append("alias_changed")
    if entry and entry.provider and model.provider and entry.provider != model.provider:
        drift_reasons.append("backend_provider_changed")
    if entry and entry.model_file_path and runtime_path and Path(entry.model_file_path).resolve() != Path(runtime_path).resolve():
        drift_reasons.append("runtime_path_changed")
    if expected_manifest_hash and expected_manifest_hash != observed_manifest_hash:
        drift_reasons.append("manifest_mismatch")
    if expected_checksum and expected_checksum != "manifest-only" and observed_checksum and expected_checksum != observed_checksum:
        drift_reasons.append("checksum_mismatch")
    if runtime_path and not Path(runtime_path).exists():
        drift_reasons.append("missing_runtime_file")

    return {
        "expected_manifest_hash": expected_manifest_hash,
        "observed_manifest_hash": observed_manifest_hash,
        "expected_checksum": expected_checksum,
        "observed_checksum": observed_checksum,
        "runtime_manifest": runtime_manifest,
        "drift_reasons": drift_reasons,
    }


async def validate_runtime_attestation(
    db: AsyncSession,
    attestation: CommercialRuntimeModelAttestation,
) -> CommercialRuntimeModelAttestation:
    reasons: list[str] = []
    if attestation.expected_manifest_hash and attestation.observed_manifest_hash:
        if attestation.expected_manifest_hash != attestation.observed_manifest_hash:
            reasons.append("manifest_mismatch")
    if attestation.expected_checksum and attestation.expected_checksum != "manifest-only" and attestation.observed_checksum:
        if attestation.expected_checksum != attestation.observed_checksum:
            reasons.append("checksum_mismatch")
    if attestation.observed_checksum is None and attestation.expected_checksum and attestation.expected_checksum != "manifest-only":
        reasons.append("missing_runtime_file")

    if attestation.attestation_status == "quarantined":
        pass
    elif reasons:
        attestation.attestation_status = "drift"
    elif attestation.expected_manifest_hash or attestation.expected_checksum:
        attestation.attestation_status = "verified"
    else:
        attestation.attestation_status = "unknown"
    await db.flush()
    return attestation


async def collect_runtime_attestation(
    db: AsyncSession,
    *,
    model: ModelRegistry,
    entry: CommercialSignedModelRegistryEntry | None = None,
    backend_name: str | None = None,
    node_id: str | None = None,
    cluster_id: str | None = None,
    settings: Settings | None = None,
) -> CommercialRuntimeModelAttestation:
    comparison = await compare_runtime_vs_registry(model, entry, settings=settings)
    attestation = CommercialRuntimeModelAttestation(
        registry_entry_id=entry.id if entry else None,
        model_name=model.model_id,
        backend_name=backend_name or (model.inference_backend.name if model.inference_backend else None),
        model_alias=model.model_alias,
        expected_manifest_hash=comparison["expected_manifest_hash"],
        observed_manifest_hash=comparison["observed_manifest_hash"],
        expected_checksum=comparison["expected_checksum"],
        observed_checksum=comparison["observed_checksum"],
        attestation_status="unknown",
        attested_at=utc_now(),
        node_id=node_id,
        cluster_id=cluster_id,
    )
    db.add(attestation)
    await db.flush()
    return await validate_runtime_attestation(db, attestation)


async def generate_boot_attestation(
    db: AsyncSession,
    models: list[ModelRegistry],
    registry_map: dict[str, CommercialSignedModelRegistryEntry],
    *,
    node_id: str | None = None,
    cluster_id: str | None = None,
    settings: Settings | None = None,
) -> list[CommercialRuntimeModelAttestation]:
    records: list[CommercialRuntimeModelAttestation] = []
    for model in models:
        entry = registry_map.get(model.model_alias or "") or registry_map.get(model.model_id)
        record = await collect_runtime_attestation(
            db,
            model=model,
            entry=entry,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=settings,
        )
        records.append(record)
    return records


def serialize_runtime_attestation(
    attestation: CommercialRuntimeModelAttestation,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload(
        {
            "id": str(attestation.id),
            "registry_entry_id": str(attestation.registry_entry_id) if attestation.registry_entry_id else None,
            "model_name": attestation.model_name,
            "backend_name": attestation.backend_name,
            "model_alias": attestation.model_alias,
            "expected_manifest_hash": _short(attestation.expected_manifest_hash),
            "observed_manifest_hash": _short(attestation.observed_manifest_hash),
            "expected_checksum": _short(attestation.expected_checksum),
            "observed_checksum": _short(attestation.observed_checksum),
            "attestation_status": attestation.attestation_status,
            "attested_at": attestation.attested_at.isoformat() if attestation.attested_at else None,
            "node_id": attestation.node_id,
            "cluster_id": attestation.cluster_id,
        }
    )
