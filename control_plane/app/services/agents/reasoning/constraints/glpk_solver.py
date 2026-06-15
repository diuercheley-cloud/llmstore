# Owner: agent-platform
import logging
from typing import Any

from .constraint_model import ConstraintModel

logger = logging.getLogger(__name__)


class GLPKSolver:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    async def solve(
        self, model: ConstraintModel, plan_data: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        if not self.enabled:
            return False, "capability_unavailable", {}

        logger.info("Solving constraints with GLPK solver...")
        # Mock success for now
        return True, "sat", {"solver": "glpk"}
