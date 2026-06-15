# Owner: agent-platform
import uuid
from typing import Any

from app.services.agents import agent_state
from sqlalchemy.ext.asyncio import AsyncSession


class PolicyDenialError(ValueError):
    """Raised when agent activation policy denies run initiation."""

    pass


def sanitize_payload(payload: Any) -> Any:
    """
    Recursively redacts dictionary values where keys contain sensitive words.
    Redacts dict keys containing: prompt, secret, token, api_key, api-key, password, key, authorization, credential.
    """
    sensitive_keys = {
        "prompt",
        "secret",
        "token",
        "api_key",
        "api-key",
        "password",
        "key",
        "authorization",
        "credential",
    }
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    else:
        return payload


async def validate_and_start_run(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tenant_id: str,
    input_text: str,
    user_id: str | None = None,
    correlation_id: str | None = None,
    session_id: uuid.UUID | None = None,
    is_admin: bool = False,
    is_simulation: bool = False,
) -> Any:
    """
    Validates the agent and starts a run.
    Ensures tenant isolation, policy checking for non-admins, and status validation.
    """
    agent = await agent_state.get_agent_definition(db, agent_id)
    if not agent:
        raise ValueError(f"Agent definition not found: {agent_id}")

    if not is_admin:
        # Tenant isolation
        if agent.tenant_id != str(tenant_id):
            raise ValueError(f"Agent definition not found: {agent_id}")

        # Agent status
        if agent.status not in ["active", "approved"]:
            raise ValueError(f"Agent is not active (current status: {agent.status})")

        # Policy Check
        from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision

        policy_engine = AgentPolicyEngine(db)
        decision, reason = await policy_engine.evaluate_agent_activation(agent)
        if decision == PolicyDecision.DENY:
            raise PolicyDenialError(f"Policy denial: {reason}")
    else:
        if agent.status == "deprecated":
            raise ValueError("Cannot execute a deprecated agent definition.")

    from types import SimpleNamespace

    from app.services.agents.agent_runtime_client import get_agent_runtime_client

    client = get_agent_runtime_client()
    run = await client.start_run(
        db=db,
        agent_id=agent_id,
        tenant_id=str(tenant_id),
        input_text=input_text,
        user_id=user_id,
        correlation_id=correlation_id,
        session_id=session_id,
        is_simulation=is_simulation,
    )

    # Simple wrapper for remote dict response to match expected object interface
    if isinstance(run, dict):
        return SimpleNamespace(**run)
    return run


async def validate_and_cancel_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: str | None = None,
    is_admin: bool = False,
) -> Any:
    """
    Validates run ownership/existence and cancels it.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError("Agent run not found")

    if not is_admin:
        if run.tenant_id != str(tenant_id):
            raise ValueError("Agent run not found")
        if run.status in ["completed", "failed", "cancelled"]:
            return run

    from app.services.agents.agent_runtime_client import get_agent_runtime_client

    client = get_agent_runtime_client()
    res = await client.cancel_run(db, run_id)
    if isinstance(res, dict):
        # We need to return the run object/namespace
        run.status = res.get("status", "cancelled")
        return run
    return res


async def validate_and_pause_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: str | None = None,
    is_admin: bool = False,
) -> Any:
    """
    Validates run ownership and pauses it.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError("Agent run not found")

    if not is_admin and run.tenant_id != str(tenant_id):
        raise ValueError("Agent run not found")

    from app.services.agents.agent_runtime_client import get_agent_runtime_client

    client = get_agent_runtime_client()
    res = await client.pause_run(db, run_id)
    if isinstance(res, dict):
        run.status = res.get("status", "paused")
        return run
    return res


async def validate_and_resume_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: str | None = None,
    is_admin: bool = False,
) -> Any:
    """
    Validates run ownership and resumes it.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError("Agent run not found")

    if not is_admin and run.tenant_id != str(tenant_id):
        raise ValueError("Agent run not found")

    from app.services.agents.agent_runtime_client import get_agent_runtime_client

    client = get_agent_runtime_client()
    res = await client.resume_run(db, run_id)
    if isinstance(res, dict):
        run.status = res.get("status", "running")
        return run
    return res


async def validate_and_replay_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: str | None = None,
    is_admin: bool = False,
) -> dict[str, Any]:
    """
    Validates run ownership and replays it.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError("Agent run not found")

    if not is_admin and run.tenant_id != str(tenant_id):
        raise ValueError("Agent run not found")

    from app.services.agents import agent_runtime

    return await agent_runtime.replay_run(db, run_id)
