# Owner: agent-platform
import uuid
from typing import List

from app.models.agents.agent_cognitive_loopback import (
    AgentFeedbackEvent,
    AgentLearningCandidate,
    AgentSuccessPattern,
)
from app.models.agents.agents import AgentRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class LearningCandidateRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_pattern(self, pattern: AgentSuccessPattern) -> AgentLearningCandidate:
        # Fetch actual data from the last run that matched this pattern or use pattern data
        # For simplicity, we just create a candidate with placeholder data
        candidate = AgentLearningCandidate(
            agent_id=pattern.agent_id,
            tenant_id=pattern.tenant_id,
            candidate_data={
                "input": f"Pattern match for fingerprint {pattern.input_fingerprint}",
                "reasoning": pattern.success_reason,
                "tools": pattern.tool_sequence,
                "answer": "Extracted from successful run"
            },
            validation_status="pending"
        )
        self.db.add(candidate)
        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def create_from_feedback(self, event: AgentFeedbackEvent) -> AgentLearningCandidate:
        # Fetch run data
        stmt = select(AgentRun).where(AgentRun.id == event.run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        
        input_text = run.input_text if run else "Feedback-driven input"
        
        candidate = AgentLearningCandidate(
            agent_id=event.agent_id,
            source_run_id=event.run_id,
            tenant_id=event.tenant_id,
            candidate_data={
                "input": input_text,
                "reasoning": "Feedback-approved path",
                "tools": [],
                "answer": event.correction_text or "Original answer approved"
            },
            validation_status="pending"
        )
        self.db.add(candidate)
        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def list_candidates(self, agent_id: uuid.UUID, tenant_id: str) -> List[AgentLearningCandidate]:
        stmt = select(AgentLearningCandidate).where(
            AgentLearningCandidate.agent_id == agent_id,
            AgentLearningCandidate.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
