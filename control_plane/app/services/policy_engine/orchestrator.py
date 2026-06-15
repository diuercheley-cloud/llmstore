import logging

from app.services.policy_engine.base import (
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
)
from app.services.policy_engine.engines.builtin_policy_engine import BuiltinPolicyEngine
from app.services.policy_engine.engines.cedar_policy_engine import CedarPolicyEngine
from app.services.policy_engine.engines.opa_policy_engine import OPAPolicyEngine

logger = logging.getLogger(__name__)


class PolicyEngineOrchestrator:
    def __init__(self):
        self.engines: list[PolicyEngine] = [
            BuiltinPolicyEngine(),
            OPAPolicyEngine(),
            CedarPolicyEngine(),
        ]

    async def evaluate(
        self, context: PolicyContext, preferred_engine: str = "builtin"
    ) -> PolicyDecision:
        """
        Evaluates the context using the preferred engine, with fallback to builtin.
        """
        # 1. Find the preferred engine
        engine = next((e for e in self.engines if e.get_engine_name() == preferred_engine), None)

        if not engine:
            logger.warning(f"Engine {preferred_engine} not found, falling back to builtin.")
            engine = self.engines[0]  # Builtin is first

        try:
            decision = await engine.evaluate(context)
            return decision
        except Exception as e:
            logger.error(
                f"Error evaluating policy with {preferred_engine}: {e}. Falling back to builtin."
            )
            if engine != self.engines[0]:
                return await self.engines[0].evaluate(context)
            raise

    async def evaluate_multi(self, context: PolicyContext) -> list[PolicyDecision]:
        """Runs all engines and returns all decisions (for comparison)."""
        decisions = []
        for engine in self.engines:
            try:
                decisions.append(await engine.evaluate(context))
            except Exception as e:
                logger.error(f"Engine {engine.get_engine_name()} failed: {e}")
        return decisions
