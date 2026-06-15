import logging

from app.core.config import get_settings
from app.models.agents.agent_optimization import AgentOptimizationCandidate, AgentOptimizationResult

logger = logging.getLogger(__name__)


class OptimizationGate:
    def can_promote(
        self, candidate: AgentOptimizationCandidate, result: AgentOptimizationResult
    ) -> bool:
        """
        Enforces promotion gate policies.
        Blocks promotion if:
        1. Optimization worsens safety (safety_failure_delta > 0 or safety_regression is True).
        2. Candidate has not been approved (status != "approved").
        """
        settings = get_settings()

        # 1. Safety regression gate (must check safety failure delta and flags)
        safety_delta = result.metrics_delta.get("safety_failure_delta", 0)
        policy_denial_delta = result.metrics_delta.get("policy_denial_delta", 0)

        if safety_delta > 0:
            logger.warning(
                f"Candidate {candidate.id} blocked: Safety failure delta is positive ({safety_delta})."
            )
            return False

        if candidate.safety_regression:
            logger.warning(f"Candidate {candidate.id} blocked: Safety regression flag is active.")
            return False

        # 2. Mandatory approval check
        # Prompt: "Nunca aplicar em production sem approval. Promotion gate obrigatório. Approval obrigatório para apply."
        # Even if settings.agent_auto_promote_optimizations is True, we enforce approval checks.
        if candidate.status != "approved":
            logger.warning(
                f"Candidate {candidate.id} blocked: Requires explicit approval. Current status: '{candidate.status}'."
            )
            return False

        return True
