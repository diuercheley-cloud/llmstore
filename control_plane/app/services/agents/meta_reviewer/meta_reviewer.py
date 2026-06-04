# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List, Tuple

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_meta_reviewer import (
    AgentMetaReview,
    AgentMetaReviewDecision,
    AgentMetaReviewFinding,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .ethical_risk_checker import EthicalRiskChecker
from .hallucination_checker import HallucinationChecker
from .policy_drift_checker import PolicyDriftChecker
from .reviewer_decision_engine import ReviewerDecisionEngine

logger = logging.getLogger(__name__)

class MetaReviewerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.hallucination = HallucinationChecker()
        self.policy = PolicyDriftChecker()
        self.ethical = EthicalRiskChecker()
        self.engine = ReviewerDecisionEngine()

    async def review_response(
        self,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        tenant_id: str,
        response: str,
        evidence: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Runs full meta-review on an agent response.
        Returns (decision, reasoning).
        """
        if not self.settings.agent_meta_reviewer_enabled:
            return "allow", "Meta-reviewer is disabled."

        review = AgentMetaReview(
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            status="pending"
        )
        self.db.add(review)
        await self.db.flush()

        all_findings = []
        
        # 1. Hallucination Check
        hall_findings = await self.hallucination.check(response, evidence)
        all_findings.extend(hall_findings)
        
        # 2. Ethical Risk Check
        eth_findings = await self.ethical.check(response)
        all_findings.extend(eth_findings)
        
        # 3. Policy Drift (General context)
        pol_findings = await self.policy.check("final_response", context)
        all_findings.extend(pol_findings)

        # Persist findings
        for f_data in all_findings:
            finding = AgentMetaReviewFinding(
                review_id=review.id,
                checker_type=f_data["checker_type"],
                severity=f_data["severity"],
                description=f_data["description"],
                evidence=f_data.get("evidence")
            )
            self.db.add(finding)

        # Consolidate Decision
        decision, reasoning = self.engine.consolidate(all_findings)
        
        blocking = self.settings.agent_meta_reviewer_blocking_mode and decision in ["block", "require_human_approval"]

        review_decision = AgentMetaReviewDecision(
            review_id=review.id,
            decision=decision,
            reasoning=reasoning,
            blocking_action_taken=blocking
        )
        self.db.add(review_decision)
        
        review.overall_decision = decision
        review.status = "completed"
        review.completed_at = utc_now()
        
        await self.db.commit()
        
        return decision, reasoning
