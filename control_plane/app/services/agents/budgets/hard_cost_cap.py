import logging

from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.agent_state import log_run_event, update_run
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("hard_cost_cap")


class HardCostCapService:
    @classmethod
    async def check_cost_cap(
        cls,
        db: AsyncSession,
        agent_def: AgentDefinition,
        run: AgentRun
    ) -> bool:
        """
        Validates if the run has exceeded the agent definition's hard cost cap (max_cost_brl).
        If exceeded, transitions run to 'failed', records a 'budget.exceeded' run event,
        and returns False to block further execution.
        """
        settings = get_settings()
        if not settings.agent_hard_cost_cap_enabled:
            return True

        max_cost = agent_def.max_cost_brl
        if max_cost is None:
            return True

        current_cost = run.estimated_cost_brl or 0.0

        if current_cost >= max_cost:
            reason = f"Hard cost cap exceeded: current cost {current_cost:.4f} BRL >= limit {max_cost:.4f} BRL"
            logger.warning(f"Run {run.id} halted. {reason}")

            # Transition run to failed (fail-safe)
            await update_run(
                db=db,
                run_id=run.id,
                status="failed",
                failure_reason=reason
            )

            # Generate run event
            await log_run_event(
                db=db,
                run_id=run.id,
                event_type="budget.exceeded",
                payload={
                    "current_cost": current_cost,
                    "max_cost": max_cost,
                    "reason": reason
                }
            )

            return False

        return True
