# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from .feedback_collector import FeedbackCollector
from .learning_candidate_registry import LearningCandidateRegistry
from .success_pattern_miner import SuccessPatternMiner

logger = logging.getLogger(__name__)


class CognitiveLoopbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.feedback = FeedbackCollector(db)
        self.miner = SuccessPatternMiner(db)
        self.candidates = LearningCandidateRegistry(db)

    async def process_run_completion(self, run_id: uuid.UUID):
        """
        Triggered when an agent run completes.
        Analyzes the run for success patterns if loopback is enabled.
        """
        if not self.settings.agent_cognitive_loopback_enabled:
            return

        logger.info(f"Processing cognitive loopback for run {run_id}")
        pattern = await self.miner.mine_run(run_id)
        if pattern:
            await self.candidates.create_from_pattern(pattern)

    async def submit_feedback(
        self,
        agent_id: uuid.UUID,
        run_id: uuid.UUID | None,
        tenant_id: str,
        feedback_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Records human feedback and potentially triggers learning.
        """
        event = await self.feedback.record(agent_id, run_id, tenant_id, feedback_data)

        if self.settings.agent_feedback_learning_enabled:
            if feedback_data.get("feedback_type") in ["thumbs_up", "approved"]:
                await self.candidates.create_from_feedback(event)

        return {"status": "feedback_recorded", "event_id": str(event.id)}
