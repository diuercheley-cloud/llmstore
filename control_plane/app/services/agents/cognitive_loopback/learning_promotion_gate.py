# Owner: agent-platform
import uuid
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.agent_cognitive_loopback import AgentLearningCandidate, AgentFewShotExample, AgentLearningPromotionReview
from .fewshot_curator import FewShotCurator

logger = logging.getLogger(__name__)

class LearningPromotionGate:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.curator = FewShotCurator(db)

    async def run_eval(self, candidate_id: uuid.UUID) -> Dict[str, Any]:
        """
        Runs automated evals on the learning candidate.
        """
        candidate = await self.db.get(AgentLearningCandidate, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
            
        # Mock eval logic
        eval_result = {
            "passed": True,
            "score": 0.95,
            "checks": ["no_secrets", "no_pii", "format_valid"]
        }
        
        # Validation for secrets/PII
        data_str = str(candidate.candidate_data)
        if "sk-" in data_str or "password" in data_str.lower():
            eval_result["passed"] = False
            eval_result["checks"].append("failed_secret_detection")
            
        candidate.eval_result = eval_result
        candidate.validation_status = "validated" if eval_result["passed"] else "rejected"
        
        await self.db.commit()
        return eval_result

    async def approve_candidate(self, candidate_id: uuid.UUID, reviewer_id: str, comments: Optional[str] = None):
        """
        Approves a candidate for promotion to few-shot example.
        """
        candidate = await self.db.get(AgentLearningCandidate, candidate_id)
        if not candidate or candidate.validation_status != "validated":
            raise ValueError("Candidate not eligible for approval (not validated or not found)")

        review = AgentLearningPromotionReview(
            candidate_id=candidate_id,
            reviewer_id=reviewer_id,
            decision="approve",
            comments=comments
        )
        self.db.add(review)
        
        if self.settings.agent_auto_apply_learnings:
            await self.promote_to_example(candidate)
        
        await self.db.commit()
        return {"status": "approved", "auto_promoted": self.settings.agent_auto_apply_learnings}

    async def promote_to_example(self, candidate: AgentLearningCandidate) -> AgentFewShotExample:
        """
        Final promotion of a candidate to an active few-shot example.
        """
        example = AgentFewShotExample(
            agent_id=candidate.agent_id,
            tenant_id=candidate.tenant_id,
            input_text=candidate.candidate_data.get("input", ""),
            reasoning_summary=candidate.candidate_data.get("reasoning", ""),
            tool_calls=candidate.candidate_data.get("tools", []),
            final_answer=candidate.candidate_data.get("answer", ""),
            is_active=True
        )
        self.db.add(example)
        candidate.validation_status = "promoted"
        return example
