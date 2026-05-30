# Owner: agent-platform
import uuid
from typing import Any, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents import agent_state

class PolicyDenialError(ValueError):
    """Raised when agent activation policy denies run initiation."""
    pass

def sanitize_payload(payload: Any) -> Any:
    """
    Recursively redacts dictionary values where keys contain sensitive words.
    Redacts dict keys containing: prompt, secret, token, api_key, api-key, password, key, authorization, credential.
    """
    sensitive_keys = {
        "prompt", "secret", "token", "api_key", "api-key", 
        "password", "key", "authorization", "credential"
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
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    session_id: Optional[uuid.UUID] = None,
    is_admin: bool = False,
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

    from app.services.agents import agent_runtime
    run = await agent_runtime.start_run(
        db=db,
        agent_id=agent_id,
        tenant_id=str(tenant_id),
        input_text=input_text,
        user_id=user_id,
        correlation_id=correlation_id,
        session_id=session_id,
    )
    return run

async def validate_and_cancel_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: Optional[str] = None,
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
            
    from app.services.agents import agent_runtime
    run = await agent_runtime.cancel_run(db, run_id)
    return run

async def validate_and_pause_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: Optional[str] = None,
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
            
    from app.services.agents import agent_runtime
    return await agent_runtime.pause_run(db, run_id)

async def validate_and_resume_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: Optional[str] = None,
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
            
    from app.services.agents import agent_runtime
    return await agent_runtime.resume_run(db, run_id)

async def validate_and_replay_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: Optional[str] = None,
    is_admin: bool = False,
) -> Dict[str, Any]:
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
