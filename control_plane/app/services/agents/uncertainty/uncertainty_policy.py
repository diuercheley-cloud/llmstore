# Owner: agent-platform
import uuid
import logging
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import get_settings
from app.models.agent_uncertainty import AgentUncertaintyPolicy, AgentUncertaintyEvent, AgentConfidenceScore
from app.models.agents import AgentDefinition

logger = logging.getLogger(__name__)

class UncertaintyPolicyEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_policy(self, agent_id: uuid.UUID) -> AgentUncertaintyPolicy:
        stmt = select(AgentUncertaintyPolicy).where(AgentUncertaintyPolicy.agent_id == agent_id)
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()
        
        if not policy:
            # Default threshold based on agent class
            agent = await self.db.get(AgentDefinition, agent_id)
            threshold = 0.7
            if agent:
                if agent.agent_class in ["compliance", "security"]: threshold = 0.9
                elif agent.agent_class == "support": threshold = 0.7
                elif agent.agent_class == "creative": threshold = 0.4
            
            policy = AgentUncertaintyPolicy(
                agent_id=agent_id,
                min_confidence_threshold=threshold,
                auto_research_enabled=self.settings.agent_uncertainty_auto_research_enabled,
                hitl_on_low_confidence=self.settings.agent_uncertainty_hitl_enabled
            )
            self.db.add(policy)
            await self.db.commit()
            await self.db.refresh(policy)
            
        return policy

    async def apply_policy(self, agent_id: uuid.UUID, run_id: uuid.UUID, estimation: Dict[str, Any]) -> Tuple[str, str]:
        """
        Decides the action to take based on confidence score and policy.
        """
        policy = await self.get_policy(agent_id)
        confidence = estimation["confidence_score"]
        
        action = "none"
        reason = "Confidence above threshold"
        
        if confidence < policy.min_confidence_threshold:
            if policy.auto_research_enabled:
                action = "research"
                reason = f"Confidence {confidence} below threshold {policy.min_confidence_threshold}. Triggering auto-research."
            elif policy.hitl_on_low_confidence:
                action = "hitl"
                reason = f"Confidence {confidence} below threshold {policy.min_confidence_threshold}. Escalating to Human-in-the-Loop."
            else:
                action = "uncertain_response"
                reason = f"Confidence {confidence} below threshold {policy.min_confidence_threshold}. Providing explicit uncertainty response."

        # Record Score
        score_record = AgentConfidenceScore(run_id=run_id, score=confidence)
        self.db.add(score_record)

        # Record Event
        agent = await self.db.get(AgentDefinition, agent_id)
        event = AgentUncertaintyEvent(
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=agent.tenant_id if agent else "unknown",
            confidence_score=confidence,
            action_taken=action,
            policy_triggered=str(policy.id),
            metrics=estimation["metrics"]
        )
        self.db.add(event)
        
        await self.db.commit()
        return action, reason
