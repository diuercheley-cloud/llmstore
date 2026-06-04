from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.commercial_attestation_runtime import (
    CommercialRuntimeMeasurement,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_payload(payload: dict[str, Any]) -> str:
    return _hash_bytes(_canonical_json(payload).encode("utf-8"))


def _environment_fingerprint() -> str:
    import os
    import platform
    parts = [
        platform.platform(),
        platform.machine(),
        platform.python_version(),
        str(os.getpid()),
    ]
    return _hash_bytes("|".join(parts).encode("utf-8"))


def _compute_file_hash(file_path: str) -> str | None:
    import os
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            return _hash_bytes(f.read())
    except (OSError, PermissionError):
        return None


async def snapshot_runtime_measurement(
    db: AsyncSession,
    *,
    cluster_id: str,
    node_id: str | None = None,
    measurement_type: str = "runtime_binary",
    object_name: str | None = None,
    object_version: str | None = None,
    object_path: str | None = None,
    expected_hash: str | None = None,
    environment_fingerprint: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    object_path_hash = _hash_payload({"path": object_path}) if object_path else None
    observed_hash = _compute_file_hash(object_path) if object_path else None

    drift_detected = False
    drift_reasons: list[str] = []
    if expected_hash and observed_hash and expected_hash != observed_hash:
        drift_detected = True
        drift_reasons.append("hash_mismatch")
    if object_path and observed_hash is None:
        drift_detected = True
        drift_reasons.append("file_not_found")

    env_fp = environment_fingerprint or _environment_fingerprint()

    measurement_data = sanitize_report_payload({
        "measurement_type": measurement_type,
        "object_name": object_name,
        "object_version": object_version,
        "object_path_hash": object_path_hash,
        "expected_hash": expected_hash,
        "observed_hash": observed_hash,
        "environment_fingerprint": env_fp,
    })
    measurement_hash = _hash_payload(measurement_data)

    prev_measurement = None
    if runtime_attestation_id:
        result = await db.execute(
            select(CommercialRuntimeMeasurement)
            .where(CommercialRuntimeMeasurement.runtime_attestation_id == runtime_attestation_id)
            .order_by(CommercialRuntimeMeasurement.created_at.desc())
            .limit(1)
        )
        prev_measurement = result.scalars().first()

    previous_measurement_hash = prev_measurement.measurement_hash if prev_measurement else None

    chain_parts = [measurement_hash]
    if previous_measurement_hash:
        chain_parts.insert(0, previous_measurement_hash)
    measurement_chain_hash = _hash_bytes(":".join(chain_parts).encode("utf-8"))

    record = CommercialRuntimeMeasurement(
        runtime_attestation_id=runtime_attestation_id,
        node_id=node_id,
        cluster_id=cluster_id,
        measurement_type=measurement_type,
        measurement_hash=measurement_hash,
        measurement_chain_hash=measurement_chain_hash,
        previous_measurement_hash=previous_measurement_hash,
        object_name=object_name,
        object_version=object_version,
        object_path_hash=object_path_hash,
        expected_hash=expected_hash,
        observed_hash=observed_hash,
        drift_detected=drift_detected,
        drift_reasons_json=drift_reasons,
        environment_fingerprint=env_fp,
        measurement_json=measurement_data,
        status="drift" if drift_detected else "valid",
        measured_at=utc_now(),
    )
    db.add(record)
    await db.flush()
    return record


async def snapshot_loaded_models(
    db: AsyncSession,
    *,
    cluster_id: str,
    model_paths: list[dict[str, Any]],
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> list[CommercialRuntimeMeasurement]:
    records: list[CommercialRuntimeMeasurement] = []
    for mp in model_paths:
        record = await snapshot_runtime_measurement(
            db,
            cluster_id=cluster_id,
            node_id=node_id,
            measurement_type="loaded_model",
            object_name=mp.get("name"),
            object_version=mp.get("version"),
            object_path=mp.get("path"),
            expected_hash=mp.get("expected_hash"),
            runtime_attestation_id=runtime_attestation_id,
        )
        records.append(record)
    return records


async def snapshot_workflow_hash(
    db: AsyncSession,
    *,
    cluster_id: str,
    workflow_id: str,
    workflow_hash: str,
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    return await snapshot_runtime_measurement(
        db,
        cluster_id=cluster_id,
        node_id=node_id,
        measurement_type="workflow_hash",
        object_name=workflow_id,
        object_version=None,
        object_path=None,
        expected_hash=workflow_hash,
        runtime_attestation_id=runtime_attestation_id,
    )


async def snapshot_policy_bundle(
    db: AsyncSession,
    *,
    cluster_id: str,
    bundle_name: str,
    bundle_hash: str,
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    return await snapshot_runtime_measurement(
        db,
        cluster_id=cluster_id,
        node_id=node_id,
        measurement_type="policy_bundle",
        object_name=bundle_name,
        expected_hash=bundle_hash,
        runtime_attestation_id=runtime_attestation_id,
    )


async def snapshot_routing_hash(
    db: AsyncSession,
    *,
    cluster_id: str,
    routing_id: str,
    routing_hash: str,
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    return await snapshot_runtime_measurement(
        db,
        cluster_id=cluster_id,
        node_id=node_id,
        measurement_type="routing_hash",
        object_name=routing_id,
        expected_hash=routing_hash,
        runtime_attestation_id=runtime_attestation_id,
    )


async def snapshot_runtime_binary(
    db: AsyncSession,
    *,
    cluster_id: str,
    binary_path: str,
    binary_version: str | None = None,
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    return await snapshot_runtime_measurement(
        db,
        cluster_id=cluster_id,
        node_id=node_id,
        measurement_type="runtime_binary",
        object_name=binary_path,
        object_version=binary_version,
        object_path=binary_path,
        runtime_attestation_id=runtime_attestation_id,
    )


async def snapshot_environment_fingerprint(
    db: AsyncSession,
    *,
    cluster_id: str,
    node_id: str | None = None,
    runtime_attestation_id: uuid.UUID | None = None,
) -> CommercialRuntimeMeasurement:
    fp = _environment_fingerprint()
    record = CommercialRuntimeMeasurement(
        runtime_attestation_id=runtime_attestation_id,
        node_id=node_id,
        cluster_id=cluster_id,
        measurement_type="environment_fingerprint",
        measurement_hash=_hash_payload({"fingerprint": fp}),
        environment_fingerprint=fp,
        measurement_json={"fingerprint": fp},
        status="valid",
        measured_at=utc_now(),
    )
    db.add(record)
    await db.flush()
    return record


async def get_measurement_history(
    db: AsyncSession,
    *,
    measurement_type: str | None = None,
    cluster_id: str | None = None,
    limit: int = 50,
) -> list[CommercialRuntimeMeasurement]:
    query = select(CommercialRuntimeMeasurement)
    if measurement_type:
        query = query.where(CommercialRuntimeMeasurement.measurement_type == measurement_type)
    if cluster_id:
        query = query.where(CommercialRuntimeMeasurement.cluster_id == cluster_id)
    query = query.order_by(CommercialRuntimeMeasurement.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def summarize_measurements(db: AsyncSession) -> dict[str, Any]:
    total = (await db.execute(select(func.count(CommercialRuntimeMeasurement.id)))).scalar() or 0
    drift = (await db.execute(
        select(func.count(CommercialRuntimeMeasurement.id))
        .where(CommercialRuntimeMeasurement.drift_detected.is_(True))
    )).scalar() or 0
    valid = (await db.execute(
        select(func.count(CommercialRuntimeMeasurement.id))
        .where(CommercialRuntimeMeasurement.status == "valid")
    )).scalar() or 0

    recent = await db.execute(
        select(CommercialRuntimeMeasurement)
        .order_by(CommercialRuntimeMeasurement.created_at.desc())
        .limit(20)
    )
    items = recent.scalars().all()

    return {
        "total_measurements": int(total),
        "drift_count": int(drift),
        "valid_count": int(valid),
        "items": [
            {
                "id": str(item.id),
                "measurement_type": item.measurement_type,
                "object_name": item.object_name,
                "status": item.status,
                "drift_detected": item.drift_detected,
                "drift_reasons": item.drift_reasons_json,
                "measured_at": item.measured_at.isoformat(),
            }
            for item in items
        ],
    }
