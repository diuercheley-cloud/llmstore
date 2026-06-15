from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_inference_reproducibility import (
    CommercialInferenceReplayEvent,
    CommercialInferenceReproducibilityRecord,
    CommercialInferenceRuntimeSnapshot,
)
from app.services.inference.reproducibility import (
    _extract_response_text,
    calculate_runtime_hash,
    compare_outputs,
    compare_runtime_snapshots,
    hash_response,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (ca != cb)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def calculate_distance(original_text: str, replay_text: str) -> float:
    max_len = max(len(original_text), len(replay_text), 1)
    distance = _levenshtein(original_text, replay_text)
    return round(min(distance / max_len, 1.0), 4)


def calculate_similarity(
    *,
    original_text: str,
    replay_text: str,
    original_hash: str,
    replay_hash: str,
    token_overlap: float | None = None,
    distance: float | None = None,
) -> float:
    if original_hash == replay_hash:
        return 1.0
    normalized_match = " ".join(original_text.lower().split()) == " ".join(
        replay_text.lower().split()
    )
    if normalized_match:
        return 0.99
    overlap = token_overlap if token_overlap is not None else 0.0
    edit_distance = (
        distance if distance is not None else calculate_distance(original_text, replay_text)
    )
    similarity = max(overlap, round(1.0 - edit_distance, 4))
    return round(min(max(similarity, 0.0), 1.0), 4)


def classify_replay_result(
    *,
    output_comparison: dict[str, Any],
    runtime_comparison: dict[str, Any],
) -> tuple[str, str]:
    if output_comparison["exact_hash_match"] and runtime_comparison["matched"]:
        return "matched", "replayed"
    if output_comparison["similarity"] >= 0.85 and not runtime_comparison["matched"]:
        return "partial_match", "drift_detected"
    if output_comparison["similarity"] >= 0.85:
        return "partial_match", "replayed"
    if output_comparison["replay_text_length"] == 0:
        return "failed", "failed"
    return "drift", "drift_detected"


async def replay_inference(
    record: CommercialInferenceReproducibilityRecord,
    *,
    replay_type: str,
    inference_callable: Callable[
        [CommercialInferenceReproducibilityRecord], Awaitable[dict[str, Any] | str | None]
    ]
    | None = None,
) -> dict[str, Any]:
    metadata = record.metadata_json or {}
    if not record.replay_supported:
        return {"ok": False, "reason": "replay_disabled", "output": None, "runtime_snapshot": None}
    if inference_callable is not None:
        output = await inference_callable(record)
        return {
            "ok": True,
            "reason": None,
            "output": output,
            "runtime_snapshot": metadata.get("replay_runtime_snapshot"),
        }
    candidate_output = metadata.get("replay_candidate_output") or metadata.get("response_text")
    if not candidate_output:
        return {
            "ok": False,
            "reason": "prompt_or_output_not_retained",
            "output": None,
            "runtime_snapshot": None,
        }
    runtime_snapshot = metadata.get("replay_runtime_snapshot")
    if isinstance(runtime_snapshot, dict) and "snapshot_hash" not in runtime_snapshot:
        runtime_snapshot["snapshot_hash"] = calculate_runtime_hash(runtime_snapshot)
    return {
        "ok": True,
        "reason": None,
        "output": candidate_output,
        "runtime_snapshot": runtime_snapshot,
    }


async def verify_replay(
    session: AsyncSession,
    *,
    record: CommercialInferenceReproducibilityRecord,
    replay_type: str,
    inference_callable: Callable[
        [CommercialInferenceReproducibilityRecord], Awaitable[dict[str, Any] | str | None]
    ]
    | None = None,
) -> dict[str, Any]:
    replay = await replay_inference(
        record, replay_type=replay_type, inference_callable=inference_callable
    )
    current_snapshot = (
        await session.execute(
            select(CommercialInferenceRuntimeSnapshot)
            .where(CommercialInferenceRuntimeSnapshot.snapshot_hash == record.runtime_config_hash)
            .order_by(desc(CommercialInferenceRuntimeSnapshot.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    current_snapshot_dict = None
    if current_snapshot is not None:
        current_snapshot_dict = {
            "backend_name": current_snapshot.backend_name,
            "runtime_engine": current_snapshot.runtime_engine,
            "runtime_engine_version": current_snapshot.runtime_engine_version,
            "model_name": current_snapshot.model_name,
            "model_manifest_hash": current_snapshot.model_manifest_hash,
            "runtime_config_json": current_snapshot.runtime_config_json or {},
            "tokenizer_info_json": current_snapshot.tokenizer_info_json or {},
            "snapshot_hash": current_snapshot.snapshot_hash,
        }

    if not replay["ok"]:
        event = CommercialInferenceReplayEvent(
            reproducibility_record_id=record.id,
            replay_type=replay_type,
            replay_result="failed",
            summary=str(replay["reason"]),
        )
        session.add(event)
        record.replay_status = "failed"
        record.replayed_at = utc_now()
        await session.flush()
        return {
            "record_id": str(record.id),
            "replay_result": "failed",
            "replay_status": "failed",
            "reason": replay["reason"],
        }

    original_output = (record.metadata_json or {}).get("response_text") or ""
    output_comparison = compare_outputs(original_output, replay["output"])
    runtime_comparison = compare_runtime_snapshots(
        current_snapshot,
        replay["runtime_snapshot"] or current_snapshot_dict,
    )
    replay_result, replay_status = classify_replay_result(
        output_comparison=output_comparison,
        runtime_comparison=runtime_comparison,
    )
    event = CommercialInferenceReplayEvent(
        reproducibility_record_id=record.id,
        replay_type=replay_type,
        replay_result=replay_result,
        similarity_score=output_comparison["similarity"],
        distance_score=output_comparison["distance"],
        replay_output_hash=hash_response(replay["output"]),
        replay_runtime_hash=calculate_runtime_hash(
            replay["runtime_snapshot"] or current_snapshot_dict
        )
        if (replay["runtime_snapshot"] or current_snapshot_dict)
        else None,
        summary=str(
            sanitize_report_payload(
                {
                    "runtime_drifts": runtime_comparison["drifts"],
                    "output_similarity": output_comparison["similarity"],
                    "best_effort": True,
                }
            )
        )[:1000],
    )
    session.add(event)
    record.replay_status = replay_status
    record.replay_similarity = output_comparison["similarity"]
    record.replay_distance = output_comparison["distance"]
    record.replayed_at = utc_now()
    await session.flush()
    return {
        "record_id": str(record.id),
        "replay_result": replay_result,
        "replay_status": replay_status,
        "similarity": output_comparison["similarity"],
        "distance": output_comparison["distance"],
        "output_comparison": output_comparison,
        "runtime_comparison": runtime_comparison,
        "drift_report": {
            "output_drift": replay_result == "drift",
            "tokenizer_drift": runtime_comparison["tokenizer_drift"],
            "template_drift": runtime_comparison["template_drift"],
            "runtime_drift": runtime_comparison["runtime_drift"],
            "quantization_drift": runtime_comparison["quantization_drift"],
            "limitations": "best-effort reproducibility only",
        },
        "replay_output_preview": _extract_response_text(
            {"choices": [{"message": {"content": replay["output"]}}]}
        )[:200]
        if isinstance(replay["output"], str)
        else _extract_response_text(replay["output"])[:200],
    }
