# Owner: agent-platform
import hashlib
import json
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.agents import (
    AgentDefinition,
    AgentRun,
    AgentRunCheckpoint,
    AgentRunEvent,
    AgentRunReceipt,
    AgentRunStep,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


def compute_sha256(content: Any) -> str:
    """Compute sha256 hash of any input serialized as canonical json or string."""
    if content is None:
        return hashlib.sha256(b"").hexdigest()
    if isinstance(content, str):
        serialized = content.encode("utf-8")
    else:
        try:
            serialized = json.dumps(content, sort_keys=True).encode("utf-8")
        except Exception:
            serialized = str(content).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


async def create_agent_definition(db: AsyncSession, data: dict) -> AgentDefinition:
    allowed_tools = data.get("allowed_tools")
    if allowed_tools is not None and not isinstance(allowed_tools, list):
        allowed_tools = list(allowed_tools)

    agent_def = AgentDefinition(
        id=data.get("id", uuid.uuid4()),
        name=data["name"],
        version=data["version"],
        description=data.get("description"),
        instructions=data["instructions"],
        model_id=data["model_id"],
        owner=data["owner"],
        tenant_id=data.get("tenant_id"),
        status=data.get("status", "draft"),
        risk_level=data.get("risk_level", "low"),
        allowed_tools=allowed_tools,
        policy_id=data.get("policy_id"),
        memory_policy_id=data.get("memory_policy_id"),
        max_steps=data.get("max_steps", 10),
        max_runtime_seconds=data.get("max_runtime_seconds", 300),
        max_tokens=data.get("max_tokens"),
        max_cost_brl=data.get("max_cost_brl"),
        agent_class=data.get("agent_class", "default"),
    )
    db.add(agent_def)
    await db.commit()
    await db.refresh(agent_def)
    logger.info(
        f"Created agent definition: {agent_def.id} (name: {agent_def.name}, version: {agent_def.version})"
    )
    return agent_def


async def get_agent_definition(db: AsyncSession, agent_id: uuid.UUID) -> AgentDefinition | None:
    res = await db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
    return res.scalar_one_or_none()


async def list_agent_definitions(
    db: AsyncSession, tenant_id: str | None = None
) -> list[AgentDefinition]:
    stmt = select(AgentDefinition)
    if tenant_id is not None:
        stmt = stmt.where(AgentDefinition.tenant_id == tenant_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def update_agent_definition(
    db: AsyncSession, agent_id: uuid.UUID, data: dict
) -> AgentDefinition | None:
    agent_def = await get_agent_definition(db, agent_id)
    if not agent_def:
        return None
    for k, v in data.items():
        if hasattr(agent_def, k):
            setattr(agent_def, k, v)
    agent_def.updated_at = utc_now()
    await db.commit()
    await db.refresh(agent_def)
    logger.info(f"Updated agent definition: {agent_def.id}")
    return agent_def


async def check_queue_throttling(db: AsyncSession, agent_id: uuid.UUID, tenant_id: str) -> None:
    from app.models.agents.agents import AgentQueueThrottle, AgentRun
    from sqlalchemy import func, select

    stmt = select(AgentQueueThrottle).where(AgentQueueThrottle.is_active == True)
    res = await db.execute(stmt)
    active_throttles = res.scalars().all()

    for throttle in active_throttles:
        applies = False
        count_stmt = select(func.count(AgentRun.id)).where(AgentRun.status == "queued")

        if throttle.target_type == "agent" and throttle.target_id == str(agent_id):
            applies = True
            count_stmt = count_stmt.where(AgentRun.agent_id == agent_id)
        elif throttle.target_type == "queue":
            if throttle.target_id == tenant_id:
                applies = True
                count_stmt = count_stmt.where(AgentRun.tenant_id == tenant_id)
            elif throttle.target_id in ("default", "global"):
                applies = True
            else:
                try:
                    target_uuid = uuid.UUID(throttle.target_id)
                    if target_uuid == agent_id:
                        applies = True
                        count_stmt = count_stmt.where(AgentRun.agent_id == agent_id)
                except ValueError:
                    applies = True
                    count_stmt = count_stmt.where(AgentRun.tenant_id == tenant_id)

        if applies:
            count_res = await db.execute(count_stmt)
            queued_count = count_res.scalar() or 0
            if queued_count >= throttle.rate_limit:
                raise ValueError(
                    f"Queue throttle limit exceeded: limit of {throttle.rate_limit} queued runs."
                )


async def create_agent_run(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tenant_id: str,
    input_text: str,
    user_id: str | None = None,
    correlation_id: str | None = None,
    parent_run_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    multimodal_asset_id: uuid.UUID | None = None,
    is_simulation: bool = False,
) -> AgentRun:
    await check_queue_throttling(db, agent_id, tenant_id)
    input_hash = compute_sha256(input_text)
    run = AgentRun(
        agent_id=agent_id,
        tenant_id=tenant_id,
        user_id=user_id,
        status="queued",
        input_text=input_text,
        input_hash=input_hash,
        total_steps=0,
        total_tokens=0,
        estimated_cost_brl=0.0,
        started_at=utc_now(),
        correlation_id=correlation_id,
        parent_run_id=parent_run_id,
        session_id=session_id,
        multimodal_asset_id=multimodal_asset_id,
        is_simulation=is_simulation,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    logger.info(
        f"Created agent run: {run.id} for agent: {agent_id} (input_hash: {input_hash}, session_id: {session_id}, is_simulation: {is_simulation})"
    )
    return run


async def get_agent_run(db: AsyncSession, run_id: uuid.UUID) -> AgentRun | None:
    res = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    return res.scalar_one_or_none()


async def update_run(db: AsyncSession, run_id: uuid.UUID, **kwargs) -> AgentRun | None:
    run = await get_agent_run(db, run_id)
    if not run:
        return None
    for k, v in kwargs.items():
        if hasattr(run, k):
            setattr(run, k, v)
    await db.commit()
    await db.refresh(run)
    logger.info(f"Updated agent run: {run.id} fields: {list(kwargs.keys())}")
    return run


async def increment_run_metric(
    db: AsyncSession, run_id: uuid.UUID, metric: str, value: float = 1.0
):
    run = await get_agent_run(db, run_id)
    if not run:
        return
    if hasattr(run, metric):
        current = getattr(run, metric) or 0
        setattr(run, metric, current + value)
    await db.commit()


import json as _json
import sys as _sys


def _emit_agent_log(run_id, event_type, data):
    structured = {
        "timestamp": utc_now().isoformat(),
        "source": "agent-runtime",
        "run_id": str(run_id),
        "event_type": event_type,
        **data,
    }
    print(_json.dumps(structured), file=_sys.stderr, flush=True)


async def log_run_step(
    db: AsyncSession,
    run_id: uuid.UUID,
    step_number: int,
    step_type: str,
    input_data: Any,
    output_data: Any,
    status: str = "success",
    latency_ms: int | None = None,
    policy_result: dict | None = None,
    metadata: dict | None = None,
    error: str | None = None,
) -> AgentRunStep:
    input_hash = compute_sha256(input_data)
    output_hash = compute_sha256(output_data)

    step = AgentRunStep(
        run_id=run_id,
        step_number=step_number,
        step_type=step_type,
        input_hash=input_hash,
        output_hash=output_hash,
        status=status,
        latency_ms=latency_ms,
        policy_result=policy_result,
        step_metadata=metadata,
        error=error,
        created_at=utc_now(),
    )
    _emit_agent_log(
        run_id,
        "run_step",
        {
            "step_number": step_number,
            "step_type": step_type,
            "status": status,
            "latency_ms": latency_ms,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "error": error,
        },
    )

    db.add(step)

    # Update total steps on the run
    run = await get_agent_run(db, run_id)
    if run:
        run.total_steps = max(run.total_steps, step_number)

    await db.commit()
    await db.refresh(step)
    logger.info(
        f"Logged step {step_number} ({step_type}) for run {run_id} (status: {status}, input_hash: {input_hash})"
    )
    return step


async def log_run_event(
    db: AsyncSession,
    run_id: uuid.UUID,
    event_type: str,
    payload: dict | None = None,
) -> AgentRunEvent:
    _emit_agent_log(
        run_id,
        "run_event",
        {
            "event_type": event_type,
            "payload": payload,
        },
    )

    event = AgentRunEvent(
        run_id=run_id,
        event_type=event_type,
        payload=payload,
        created_at=utc_now(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def create_run_checkpoint(
    db: AsyncSession,
    run_id: uuid.UUID,
    step_number: int,
    state_snapshot: dict,
) -> AgentRunCheckpoint:
    checkpoint = AgentRunCheckpoint(
        run_id=run_id,
        step_number=step_number,
        state_snapshot=state_snapshot,
        checkpoint_time=utc_now(),
        created_at=utc_now(),
    )
    db.add(checkpoint)
    await db.commit()
    await db.refresh(checkpoint)
    logger.info(f"Created checkpoint for run {run_id} at step {step_number}")
    return checkpoint


async def get_run_checkpoints(db: AsyncSession, run_id: uuid.UUID) -> list[AgentRunCheckpoint]:
    res = await db.execute(
        select(AgentRunCheckpoint)
        .where(AgentRunCheckpoint.run_id == run_id)
        .order_by(AgentRunCheckpoint.step_number.asc())
    )
    return list(res.scalars().all())


async def create_run_receipt(
    db: AsyncSession,
    run_id: uuid.UUID,
    step_number: int | None,
    receipt_data: dict,
    signature: str | None = None,
) -> AgentRunReceipt:
    receipt = AgentRunReceipt(
        run_id=run_id,
        step_number=step_number,
        receipt_data=receipt_data,
        signature=signature,
        created_at=utc_now(),
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return receipt


async def get_run_steps(db: AsyncSession, run_id: uuid.UUID) -> list[AgentRunStep]:
    res = await db.execute(
        select(AgentRunStep)
        .where(AgentRunStep.run_id == run_id)
        .order_by(AgentRunStep.step_number.asc())
    )
    return list(res.scalars().all())
