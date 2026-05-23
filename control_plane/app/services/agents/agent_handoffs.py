# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.models.agents import (
    AgentDefinition,
    AgentRun,
    AgentHandoffPolicy,
    AgentHandoffEvent,
    AgentCollaborationSession,
)
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class HandoffDeniedError(RuntimeError):
    pass

class AgentHandoffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_handoff_policy(self, data: dict) -> AgentHandoffPolicy:
        policy = AgentHandoffPolicy(
            tenant_id=data["tenant_id"],
            source_agent_id=data["source_agent_id"],
            target_agent_id=data["target_agent_id"],
            allowed_reason=data.get("allowed_reason"),
            max_handoffs_per_run=data.get("max_handoffs_per_run", 5),
            allowed_context_fields=data.get("allowed_context_fields"),
            requires_approval=data.get("requires_approval", False),
            tenant_boundary_mode=data.get("tenant_boundary_mode", "strict")
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def get_handoff_policies(self, tenant_id: str) -> List[AgentHandoffPolicy]:
        stmt = select(AgentHandoffPolicy).where(AgentHandoffPolicy.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def initiate_handoff(
        self,
        source_run_id: uuid.UUID,
        target_agent_id: uuid.UUID,
        reason: str,
        context: Dict[str, Any]
    ) -> uuid.UUID:
        if not self.settings.agent_handoffs_enabled:
            raise HandoffDeniedError("Agent handoffs are disabled.")

        res_source = await self.db.execute(select(AgentRun).where(AgentRun.id == source_run_id))
        source_run = res_source.scalar_one_or_none()
        if not source_run:
            raise ValueError("Source run not found")

        # 0. Policy Engine Check (v2)
        from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyRequest
        policy_req = PolicyRequest(
            action_type="handoff",
            subject=str(target_agent_id),
            tenant_id=source_run.tenant_id,
            agent_id=source_run.agent_id,
            run_id=source_run_id,
            context={"reason": reason}
        )
        policy_engine = AgentPolicyEngine(self.db)
        decision = await policy_engine.evaluate_action_v2(policy_req)
        if decision.result == "deny":
            raise HandoffDeniedError(f"Handoff denied by policy: {decision.reason}")

        # 1. Handoff Specific Policy Check
        stmt_policy = select(AgentHandoffPolicy).where(
            AgentHandoffPolicy.source_agent_id == source_run.agent_id,
            AgentHandoffPolicy.target_agent_id == target_agent_id,
            AgentHandoffPolicy.tenant_id == source_run.tenant_id
        )
        res_policy = await self.db.execute(stmt_policy)
        policy = res_policy.scalar_one_or_none()
        
        if not policy:
            raise HandoffDeniedError(f"No handoff policy found between source and target agent.")

        # 2. Check for Collaboration Session
        stmt_session = select(AgentCollaborationSession).where(
            AgentCollaborationSession.root_run_id == source_run_id,
            AgentCollaborationSession.status == "active"
        )
        # If not root, we need to find the session this run belongs to
        # Simplification: assume root_run_id is passed or session_id
        res_session = await self.db.execute(stmt_session)
        session = res_session.scalar_one_or_none()
        
        if not session:
            session = AgentCollaborationSession(
                tenant_id=source_run.tenant_id,
                root_run_id=source_run_id,
                handoff_count=0
            )
            self.db.add(session)
            await self.db.flush()

        if session.handoff_count >= policy.max_handoffs_per_run:
            raise HandoffDeniedError("Maximum handoffs reached for this session.")

        # 3. Context Sanitization
        sanitized_context = {}
        if policy.allowed_context_fields:
            for field in policy.allowed_context_fields:
                if field in context:
                    sanitized_context[field] = context[field]
        else:
            # If no fields specified, share nothing or a minimal set
            sanitized_context = {"reason": reason}

        # 4. Create Target Run
        target_run = await agent_state.create_agent_run(
            self.db,
            agent_id=target_agent_id,
            tenant_id=source_run.tenant_id,
            input_text=f"Handoff from {source_run.agent_id}: {reason}",
            correlation_id=f"handoff-{session.id}"
        )
        
        # 5. Log Event
        event = AgentHandoffEvent(
            session_id=session.id,
            source_run_id=source_run_id,
            target_run_id=target_run.id,
            source_agent_id=source_run.agent_id,
            target_agent_id=target_agent_id,
            reason=reason,
            context_keys=list(sanitized_context.keys())
        )
        self.db.add(event)
        
        session.handoff_count += 1
        await self.db.commit()
        return target_run.id

    async def list_run_handoffs(self, run_id: uuid.UUID) -> List[AgentHandoffEvent]:
        stmt = select(AgentHandoffEvent).where(
            (AgentHandoffEvent.source_run_id == run_id) | (AgentHandoffEvent.target_run_id == run_id)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
