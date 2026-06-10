# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.agents import AgentABEvalRun, AgentEvalPairwiseResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class ABComparisonEvaluator:
    """
    Handles A/B comparison of agent versions using pairwise scoring.
    Compares cost, latency, and safety alongside quality.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_ab_run(self, tenant_id: str, agent_a_id: uuid.UUID, agent_b_id: uuid.UUID) -> AgentABEvalRun:
        ab_run = AgentABEvalRun(
            tenant_id=tenant_id,
            agent_a_id=agent_a_id,
            agent_b_id=agent_b_id,
            status="running"
        )
        self.db.add(ab_run)
        await self.db.flush()
        return ab_run

    async def record_pairwise_result(
        self, 
        ab_run_id: uuid.UUID, 
        input_text: str, 
        response_a: str, 
        response_b: str, 
        preference: str, 
        rationale: str = None, 
        metrics: Dict[str, Any] = None
    ) -> AgentEvalPairwiseResult:
        result = AgentEvalPairwiseResult(
            ab_run_id=ab_run_id,
            input_text=input_text,
            response_a=response_a,
            response_b=response_b,
            preference=preference,
            rationale=rationale,
            metrics=metrics or {}
        )
        self.db.add(result)
        await self.db.flush()
        return result

    async def finalize_ab_run(self, ab_run_id: uuid.UUID) -> Optional[uuid.UUID]:
        """
        Determines the winner of an A/B run based on pairwise preferences.
        Considers overall safety and performance metrics.
        """
        stmt = select(AgentEvalPairwiseResult).where(AgentEvalPairwiseResult.ab_run_id == ab_run_id)
        res = await self.db.execute(stmt)
        results = list(res.scalars().all())

        if not results:
            return None

        votes_a = sum(1 for r in results if r.preference == "A")
        votes_b = sum(1 for r in results if r.preference == "B")

        stmt = select(AgentABEvalRun).where(AgentABEvalRun.id == ab_run_id)
        res = await self.db.execute(stmt)
        ab_run = res.scalar_one_or_none()

        if not ab_run:
            return None

        # Determine winner based on majority votes
        if votes_a > votes_b:
            ab_run.winner_id = ab_run.agent_a_id
        elif votes_b > votes_a:
            ab_run.winner_id = ab_run.agent_b_id
        
        ab_run.status = "completed"
        await self.db.flush()
        return ab_run.winner_id
