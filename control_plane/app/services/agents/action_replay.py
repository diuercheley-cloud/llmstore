# Owner: agent-platform
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentExecution,
    CommercialAgentReplayRecord,
)
from app.services.agents.execution_receipts import canonical_json, sha256_hex, verify_action_receipt


def build_execution_graph_hash(actions: list[CommercialAgentAction]) -> str:
    return sha256_hex(
        canonical_json(
            [action.graph_node_hash for action in sorted(actions, key=lambda row: row.action_index)]
        )
    )


async def verify_execution_replay(
    db: AsyncSession,
    *,
    execution_id: UUID,
    verified_by: str = "system",
    expected_plan: list[dict[str, Any]] | None = None,
) -> CommercialAgentReplayRecord:
    execution = await db.get(CommercialAgentExecution, execution_id)
    if execution is None:
        raise ValueError("execution_not_found")

    action_rows = (
        await db.execute(
            select(CommercialAgentAction)
            .where(CommercialAgentAction.execution_id == execution_id)
            .order_by(CommercialAgentAction.action_index.asc())
        )
    ).scalars().all()

    stored_plan = (execution.metadata_json or {}).get("plan") or []
    replay_plan = expected_plan or [
        {
            "action_index": row.get("action_index"),
            "action_name": row.get("action_name"),
            "tool_name": row.get("tool_name"),
            "requires_approval": row.get("requires_approval", False),
            "planned_input_hash": row.get("planned_input_hash"),
            "graph_node_hash": row.get("graph_node_hash"),
        }
        for row in stored_plan
    ] or [
        {
            "action_index": row.action_index,
            "action_name": row.action_name,
            "tool_name": row.tool_name,
            "requires_approval": False,
            "planned_input_hash": row.planned_input_hash,
            "graph_node_hash": row.graph_node_hash,
        }
        for row in action_rows
    ]
    replay_plan_hash = sha256_hex(canonical_json(replay_plan))
    replay_graph_hash = build_execution_graph_hash(action_rows)

    mismatch_reason = None
    verification_result = "verified"

    if execution.plan_hash and execution.plan_hash != replay_plan_hash:
        verification_result = "drift_detected"
        mismatch_reason = "plan_hash_mismatch"
    elif execution.execution_graph_hash and execution.execution_graph_hash != replay_graph_hash:
        verification_result = "drift_detected"
        mismatch_reason = "graph_hash_mismatch"
    else:
        for row in action_rows:
            if not row.receipt_hash:
                verification_result = "invalid"
                mismatch_reason = "missing_receipt"
                break
            receipt = {
                "body": {
                    "execution_id": str(row.execution_id),
                    "tenant_id": row.tenant_id,
                    "action_index": row.action_index,
                    "tool_name": row.tool_name,
                    "planned_input_hash": row.planned_input_hash,
                    "result_hash": row.result_hash,
                    "policy_decision": (row.policy_decision_json or {}).get("decision"),
                    "runtime_snapshot_hash": (row.metadata_json or {}).get("runtime_snapshot_hash"),
                    "previous_action_hash": row.previous_action_hash,
                    "execution_graph_hash": execution.execution_graph_hash,
                    "sandbox_context": row.sandbox_context_json or {},
                },
                "receipt_hash": row.receipt_hash,
                "detached_signature": row.detached_signature,
                "signature_algorithm": row.signature_algorithm,
                "immutable_hash": (row.metadata_json or {}).get("immutable_hash"),
            }
            if not verify_action_receipt(receipt):
                verification_result = "invalid"
                mismatch_reason = f"receipt_invalid:{row.action_index}"
                break

    tenant_id = execution.tenant_id or ((execution.metadata_json or {}).get("tenant_id")) or ""

    replay = CommercialAgentReplayRecord(
        execution_id=execution.id,
        tenant_id=tenant_id,
        replay_hash=sha256_hex(f"{execution.id}:{replay_plan_hash}:{replay_graph_hash}:{verification_result}"),
        original_plan_hash=execution.plan_hash,
        original_graph_hash=execution.execution_graph_hash,
        runtime_snapshot_hash=execution.runtime_snapshot_hash,
        replay_graph_hash=replay_graph_hash,
        verification_result=verification_result,
        mismatch_reason=mismatch_reason,
        verified_by=verified_by,
        metadata_json={"action_count": len(action_rows)},
        replayed_at=utc_now(),
        verified_at=utc_now(),
    )
    db.add(replay)
    execution.replay_status = verification_result
    await db.flush()
    return replay
