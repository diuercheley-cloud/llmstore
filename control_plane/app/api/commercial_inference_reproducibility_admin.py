# Owner: commercial-ops
from __future__ import annotations

import uuid
from typing import Any

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.commercial.commercial_inference_reproducibility import (
    CommercialInferenceReplayEvent,
    CommercialInferenceReproducibilityRecord,
    CommercialInferenceRuntimeSnapshot,
)
from app.services.auth import require_admin
from app.services.inference.replay_verification import verify_replay
from app.services.routing.commercial_report_export import sanitize_report_payload
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    tags=["admin", "inference-reproducibility"],
    dependencies=[Depends(require_admin)],
)


class ReplayRequestPayload(BaseModel):
    replay_type: str | None = Field(default=None, pattern="^(exact|best_effort|cross_backend)$")


def _serialize_record(item: CommercialInferenceReproducibilityRecord) -> dict[str, Any]:
    metadata = sanitize_report_payload(item.metadata_json or {})
    metadata.pop("prompt_text", None)
    metadata.pop("response_text", None)
    metadata.pop("replay_candidate_output", None)
    return {
        "id": str(item.id),
        "request_id": item.request_id,
        "correlation_id": item.correlation_id,
        "client_id": item.client_id,
        "model_name": item.model_name,
        "model_alias": item.model_alias,
        "provider": item.provider,
        "backend_name": item.backend_name,
        "tokenizer_name": item.tokenizer_name,
        "tokenizer_version": item.tokenizer_version,
        "chat_template_hash": (item.chat_template_hash or "")[:12] or None,
        "prompt_hash": item.prompt_hash[:12],
        "request_payload_hash": item.request_payload_hash[:12],
        "response_payload_hash": item.response_payload_hash[:12],
        "seed": item.seed,
        "temperature": item.temperature,
        "top_p": item.top_p,
        "top_k": item.top_k,
        "min_p": item.min_p,
        "repetition_penalty": item.repetition_penalty,
        "max_tokens": item.max_tokens,
        "runtime_engine": item.runtime_engine,
        "runtime_engine_version": item.runtime_engine_version,
        "model_manifest_hash": (item.model_manifest_hash or "")[:12] or None,
        "model_checksum": (item.model_checksum or "")[:12] or None,
        "runtime_config_hash": (item.runtime_config_hash or "")[:12] or None,
        "replay_supported": item.replay_supported,
        "replay_status": item.replay_status,
        "replay_similarity": item.replay_similarity,
        "replay_distance": item.replay_distance,
        "immutable_hash": (item.immutable_hash or "")[:12] or None,
        "metadata_json": metadata,
        "created_at": item.created_at.isoformat(),
        "replayed_at": item.replayed_at.isoformat() if item.replayed_at else None,
        "badges": [
            badge
            for badge, active in [
                ("REPLAYABLE", item.replay_supported),
                ("DRIFT", item.replay_status == "drift_detected"),
                ("EXACT_MATCH", item.replay_similarity == 1.0 and item.replay_status == "replayed"),
                ("PARTIAL_MATCH", item.replay_status == "replayed" and (item.replay_similarity or 0) < 1.0),
                ("FAILED", item.replay_status == "failed"),
            ]
            if active
        ],
    }


def _serialize_event(item: CommercialInferenceReplayEvent) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "reproducibility_record_id": str(item.reproducibility_record_id),
            "replay_type": item.replay_type,
            "replay_result": item.replay_result,
            "similarity_score": item.similarity_score,
            "distance_score": item.distance_score,
            "replay_output_hash": (item.replay_output_hash or "")[:12] or None,
            "replay_runtime_hash": (item.replay_runtime_hash or "")[:12] or None,
            "summary": item.summary,
            "created_at": item.created_at.isoformat(),
        }
    )


def _serialize_snapshot(item: CommercialInferenceRuntimeSnapshot) -> dict[str, Any]:
    cfg = sanitize_report_payload(item.runtime_config_json or {})
    tok = sanitize_report_payload(item.tokenizer_info_json or {})
    cfg.pop("backend_metadata", None)
    return {
        "id": str(item.id),
        "backend_name": item.backend_name,
        "runtime_engine": item.runtime_engine,
        "runtime_engine_version": item.runtime_engine_version,
        "model_name": item.model_name,
        "model_manifest_hash": (item.model_manifest_hash or "")[:12] or None,
        "runtime_config_json": cfg,
        "tokenizer_info_json": tok,
        "snapshot_hash": item.snapshot_hash[:12],
        "created_at": item.created_at.isoformat(),
    }


@router.get("/admin/inference/reproducibility")
async def list_reproducibility_records(
    limit: int = Query(default=100, ge=1, le=500),
    client_id: str | None = None,
    replay_status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialInferenceReproducibilityRecord).order_by(desc(CommercialInferenceReproducibilityRecord.created_at)).limit(limit)
    if client_id:
        stmt = stmt.where(CommercialInferenceReproducibilityRecord.client_id == client_id)
    if replay_status:
        stmt = stmt.where(CommercialInferenceReproducibilityRecord.replay_status == replay_status)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_record(item) for item in rows]}


@router.get("/admin/inference/reproducibility/status")
async def reproducibility_status(db: AsyncSession = Depends(get_db_session)):
    total = (await db.execute(select(func.count(CommercialInferenceReproducibilityRecord.id)))).scalar() or 0
    replayable = (
        await db.execute(
            select(func.count(CommercialInferenceReproducibilityRecord.id)).where(
                CommercialInferenceReproducibilityRecord.replay_supported.is_(True)
            )
        )
    ).scalar() or 0
    drifts = (
        await db.execute(
            select(func.count(CommercialInferenceReproducibilityRecord.id)).where(
                CommercialInferenceReproducibilityRecord.replay_status == "drift_detected"
            )
        )
    ).scalar() or 0
    successes = (
        await db.execute(
            select(func.count(CommercialInferenceReplayEvent.id)).where(
                CommercialInferenceReplayEvent.replay_result == "matched"
            )
        )
    ).scalar() or 0
    partials = (
        await db.execute(
            select(func.count(CommercialInferenceReplayEvent.id)).where(
                CommercialInferenceReplayEvent.replay_result == "partial_match"
            )
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(CommercialInferenceReplayEvent.id)).where(
                CommercialInferenceReplayEvent.replay_result == "failed"
            )
        )
    ).scalar() or 0
    snapshots = (await db.execute(select(func.count(CommercialInferenceRuntimeSnapshot.id)))).scalar() or 0
    total_events = successes + partials + failed + (
        (await db.execute(
            select(func.count(CommercialInferenceReplayEvent.id)).where(
                CommercialInferenceReplayEvent.replay_result == "drift"
            )
        )).scalar() or 0
    )
    return {
        "enabled": get_settings().commercial_reproducibility_enabled,
        "best_effort_only": True,
        "totals": {
            "records": int(total),
            "replayable": int(replayable),
            "runtime_snapshots": int(snapshots),
            "drift_detections": int(drifts),
            "replay_queue": 0,
        },
        "rates": {
            "replay_success_rate": round((successes / total_events) if total_events else 0.0, 4),
            "reproducibility_coverage": round((replayable / total) if total else 0.0, 4),
            "deterministic_replay_support_percent": round(((replayable / total) * 100.0) if total else 0.0, 2),
        },
        "badges": [
            "REPLAYABLE",
            "DRIFT",
            "EXACT_MATCH",
            "PARTIAL_MATCH",
            "FAILED",
            "TOKENIZER_DRIFT",
            "TEMPLATE_DRIFT",
        ],
    }


@router.get("/admin/inference/reproducibility/{record_id}")
async def get_reproducibility_record(record_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    item = await db.get(CommercialInferenceReproducibilityRecord, record_id)
    if item is None:
        raise HTTPException(status_code=404, detail="reproducibility record not found")
    return _serialize_record(item)


@router.post("/admin/inference/replay/{record_id}")
async def replay_record(
    record_id: uuid.UUID,
    payload: ReplayRequestPayload | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReproducibilityRecord, record_id)
    if item is None:
        raise HTTPException(status_code=404, detail="reproducibility record not found")
    replay_type = (payload.replay_type if payload else None) or get_settings().commercial_replay_default_mode
    if replay_type == "cross_backend" and not get_settings().commercial_replay_allow_cross_backend:
        raise HTTPException(status_code=403, detail="cross-backend replay is disabled")
    result = await verify_replay(db, record=item, replay_type=replay_type)
    await db.commit()
    return sanitize_report_payload(result)


@router.get("/admin/inference/replay-events")
async def list_replay_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    rows = (
        await db.execute(
            select(CommercialInferenceReplayEvent)
            .order_by(desc(CommercialInferenceReplayEvent.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return {"items": [_serialize_event(item) for item in rows]}


@router.get("/admin/inference/runtime-snapshots")
async def list_runtime_snapshots(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    rows = (
        await db.execute(
            select(CommercialInferenceRuntimeSnapshot)
            .order_by(desc(CommercialInferenceRuntimeSnapshot.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return {"items": [_serialize_snapshot(item) for item in rows]}

