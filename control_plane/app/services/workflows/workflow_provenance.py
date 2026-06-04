from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.commercial_workflows import (
    CommercialWorkflowCheckpoint,
    CommercialWorkflowDefinition,
    CommercialWorkflowExecution,
    CommercialWorkflowStage,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(payload: Any) -> str:
    if isinstance(payload, bytes):
        data = payload
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def redact_sensitive_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = key.lower()
            if any(token in lowered for token in ("secret", "token", "password", "prompt", "response", "plaintext", "input_text", "output_text")):
                redacted[key] = f"sha256:{sha256_hex(value)}"
            else:
                redacted[key] = redact_sensitive_payload(value)
        return redacted
    if isinstance(payload, list):
        return [redact_sensitive_payload(item) for item in payload]
    return payload


class WorkflowProvenanceService:
    async def build_execution_provenance(
        self,
        db: AsyncSession,
        execution: CommercialWorkflowExecution,
    ) -> dict[str, Any]:
        definition = await db.get(CommercialWorkflowDefinition, execution.definition_id)
        stage_rows = (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution.id)
                .order_by(CommercialWorkflowStage.stage_order.asc(), CommercialWorkflowStage.created_at.asc())
            )
        ).scalars().all()
        checkpoints = (
            await db.execute(
                select(CommercialWorkflowCheckpoint)
                .where(CommercialWorkflowCheckpoint.execution_id == execution.id)
                .order_by(CommercialWorkflowCheckpoint.step_index.asc(), CommercialWorkflowCheckpoint.created_at.asc())
            )
        ).scalars().all()
        provenance = sanitize_report_payload(
            {
                "execution_id": str(execution.id),
                "definition_id": str(execution.definition_id),
                "tenant_id": execution.tenant_id,
                "request_id": execution.request_id,
                "workflow_name": definition.workflow_name if definition else None,
                "definition_hash": definition.definition_hash if definition else None,
                "dag_hash": execution.dag_hash,
                "ledger_hash": execution.ledger_hash,
                "determinism_status": execution.determinism_status,
                "offline_bundle_hash": execution.offline_bundle_hash,
                "stages": [
                    {
                        "stage_key": row.stage_key,
                        "status": row.status,
                        "dependencies": row.dependencies_json or [],
                        "stage_hash": row.stage_hash,
                        "previous_stage_hash": row.previous_stage_hash,
                        "lineage_hash": row.lineage_hash,
                        "checkpoint_hash": row.checkpoint_hash,
                        "receipt_hash": row.receipt_hash,
                        "policy_gate_status": row.policy_gate_status,
                        "runtime_snapshot_hash": row.runtime_snapshot_hash,
                    }
                    for row in stage_rows
                ],
                "checkpoints": [
                    {
                        "stage_key": cp.stage_key,
                        "step_index": cp.step_index,
                        "snapshot_hash": cp.snapshot_hash,
                        "previous_checkpoint_hash": cp.previous_checkpoint_hash,
                        "immutable_hash": cp.immutable_hash,
                    }
                    for cp in checkpoints
                ],
                "metadata": redact_sensitive_payload(execution.metadata_json or {}),
            }
        )
        provenance["provenance_hash"] = sha256_hex(provenance)
        return provenance

    async def detect_pipeline_drift(
        self,
        db: AsyncSession,
        original_execution_id,
        replay_execution_id,
    ) -> dict[str, Any]:
        original = await db.get(CommercialWorkflowExecution, original_execution_id)
        replay = await db.get(CommercialWorkflowExecution, replay_execution_id)
        if original is None or replay is None:
            raise ValueError("execution_not_found")
        original_stages = (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == original.id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        ).scalars().all()
        replay_stages = (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == replay.id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        ).scalars().all()
        mismatches: list[dict[str, Any]] = []
        for index, pair in enumerate(zip(original_stages, replay_stages, strict=False)):
            if len(pair) != 2:
                break
            first, second = pair
            if first.stage_hash != second.stage_hash:
                mismatches.append(
                    {
                        "stage_index": index,
                        "stage_key": first.stage_key,
                        "original_stage_hash": first.stage_hash,
                        "replay_stage_hash": second.stage_hash,
                    }
                )
        if len(original_stages) != len(replay_stages):
            mismatches.append(
                {
                    "stage_index": min(len(original_stages), len(replay_stages)),
                    "stage_key": None,
                    "reason": "stage_count_mismatch",
                    "original_stage_count": len(original_stages),
                    "replay_stage_count": len(replay_stages),
                }
            )
        drift_detected = bool(
            mismatches
            or original.execution_hash_chain != replay.execution_hash_chain
            or original.ledger_hash != replay.ledger_hash
        )
        return {
            "drift_detected": drift_detected,
            "mismatches": mismatches,
            "original_execution_hash_chain": original.execution_hash_chain,
            "replay_execution_hash_chain": replay.execution_hash_chain,
            "original_ledger_hash": original.ledger_hash,
            "replay_ledger_hash": replay.ledger_hash,
        }
