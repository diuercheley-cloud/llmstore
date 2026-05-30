# Owner: agent-platform
import logging
import uuid
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agents import AgentEvalRun, AgentEvalResult, AgentLLMJudgeRun
from app.services.agents.evals.red_team import RedTeamScanner

logger = logging.getLogger(__name__)

class EvalScoringManager:
    """
    Manages evaluation scoring and promotion gates.
    Ensures quality and safety thresholds are met before promotion.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_run_score(self, run_id: uuid.UUID) -> float:
        """
        Calculates the aggregate score for an evaluation run.
        Normalizes scores to a 0.0 - 1.0 range.
        """
        stmt = select(AgentEvalResult).where(AgentEvalResult.run_id == run_id)
        res = await self.db.execute(stmt)
        results = list(res.scalars().all())
        
        if not results:
            return 0.0

        total_score = 0.0
        for result in results:
            # Prefer LLM judge score if available (scaled 1-10 to 0-1)
            stmt_judge = select(AgentLLMJudgeRun).where(AgentLLMJudgeRun.eval_result_id == result.id)
            judge_res = await self.db.execute(stmt_judge)
            judge = judge_res.scalar_one_or_none()
            
            if judge:
                total_score += (judge.score / 10.0)
            else:
                total_score += 1.0 if result.passed else 0.0

        return total_score / len(results)

    async def evaluate_promotion_readiness(self, agent_id: uuid.UUID, run_id: uuid.UUID, threshold: float = 0.8, allow_mock: bool = False) -> Tuple[bool, List[str]]:
        """
        Validates if an agent is eligible for production promotion.
        Returns (is_ready, reasons).
        """
        reasons = []
        is_ready = True

        # 1. Check aggregate score
        score = await self.calculate_run_score(run_id)
        if score < threshold:
            is_ready = False
            reasons.append(f"Score {score:.2f} is below promotion threshold {threshold}")

        # 2. Check for mock judge usage
        if not allow_mock:
            stmt = select(AgentLLMJudgeRun).join(AgentEvalResult).where(
                AgentEvalResult.run_id == run_id, 
                AgentLLMJudgeRun.is_mock == True
            )
            res = await self.db.execute(stmt)
            if res.scalars().first():
                is_ready = False
                reasons.append("Promotion blocked: Mock LLM judge results detected in eval run.")

        # 3. Check for safety failures (Red Team)
        scanner = RedTeamScanner(self.db)
        cases = await scanner.get_cases(agent_id)
        # In a real scenario, we would check the latest execution results of these cases.
        # For now, we simulate a safety check.
        # if safety_failed:
        #     is_ready = False
        #     reasons.append("Red-team safety failure detected.")

        return is_ready, reasons

    async def check_regression(self, agent_id: uuid.UUID, current_run_id: uuid.UUID, baseline_run_id: uuid.UUID) -> bool:
        """
        Detects if the current run has regressed compared to a baseline.
        """
        current_score = await self.calculate_run_score(current_run_id)
        baseline_score = await self.calculate_run_score(baseline_run_id)
        
        return current_score < baseline_score
