# Owner: agent-platform
import logging
from typing import Dict, Any, List
from app.core.config import get_settings
from .constraint_model import ConstraintModel
from .z3_solver import Z3Solver
from .glpk_solver import GLPKSolver
from .constraint_validator import ConstraintValidator

logger = logging.getLogger(__name__)

class ConstraintRuntime:
    def __init__(self):
        self.settings = get_settings()
        self.z3 = Z3Solver(self.settings.agent_z3_solver_enabled)
        self.glpk = GLPKSolver(self.settings.agent_glpk_solver_enabled)
        self.validator = ConstraintValidator()

    async def validate_plan(self, model: ConstraintModel, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates an agentic plan against a formal constraint model.
        """
        if not self.settings.agent_constraint_reasoning_enabled:
            return {"status": "skipped", "reason": "Constraint reasoning disabled"}

        # 1. Attempt Formal Solving if possible
        if self.settings.agent_z3_solver_enabled:
            success, result, proof = await self.z3.solve(model, plan_data)
            if success:
                return {"status": "validated", "solver": "z3", "result": result, "proof": proof}

        if self.settings.agent_glpk_solver_enabled:
            success, result, proof = await self.glpk.solve(model, plan_data)
            if success:
                return {"status": "validated", "solver": "glpk", "result": result, "proof": proof}

        # 2. Fallback to Simple Validator
        errors = self.validator.validate(model, plan_data)
        if errors:
            return {
                "status": "rejected",
                "stage": "fallback_validation",
                "errors": errors
            }

        return {"status": "validated", "stage": "fallback_validation", "message": "All simple constraints satisfied."}
