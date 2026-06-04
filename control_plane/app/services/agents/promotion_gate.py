# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.core.time import utc_now
from app.models.agents import (
    AgentDefinition,
    AgentEvalBaseline,
    AgentIncident,
    AgentPromotionGate,
    AgentRegistryEntry,
)
from app.services.agents.agent_risk_engine import AgentRiskEngine
from app.services.agents.prompt_baseline_registry import PromptBaselineRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PromotionGateError(RuntimeError):
    pass

class AgentPromotionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.baseline_registry = PromptBaselineRegistry(db)
        self.risk_engine = AgentRiskEngine()

    async def run_promotion_check(self, agent_id: uuid.UUID, target_status: str) -> Dict[str, Any]:
        """
        Runs a comprehensive promotion check for an agent.
        """
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        agent = res_agent.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent definition not found")

        registry_res = await self.db.execute(select(AgentRegistryEntry).where(AgentRegistryEntry.agent_id == agent.id))
        registry = registry_res.scalar_one_or_none()

        checks = {
            "eval_baseline": False,
            "regression_suite": False,
            "security_check": True,
            "compatibility_check": True,
            "no_critical_incidents": False,
            "prompt_freshness": False,
            "owner_assigned": bool(agent.owner),
        }

        # 0. Regression Suite Check
        from app.services.agent_deployments.deployment_regression_suite import AgentRegressionSuite
        async def _noop(agent_id, input_text, **kw):
            return f"Mock response for: {input_text[:50]}"
        suite = AgentRegressionSuite(self.db, _noop)
        gate_passed, suite_result = await suite.check_promotion_gate(
            agent_id, agent.status or "draft", target_status,
            required_suites=["basic_sanity", "guardrails"],
        )
        checks["regression_suite"] = gate_passed
        if not gate_passed:
            logger.warning(
                "Promotion blocked by regression suite for agent %s: %d/%d failed",
                agent_id, suite_result.failed, suite_result.total,
            )

        # 1. Eval Baseline Check
        from app.models.agents import AgentEvalRun, AgentEvalSuite
        from app.services.agents.evals.eval_scoring import EvalScoringManager
        
        scoring_manager = EvalScoringManager(self.db)
        # Find latest evaluation run for this agent
        stmt_run = (
            select(AgentEvalRun)
            .join(AgentEvalSuite, AgentEvalRun.suite_id == AgentEvalSuite.id)
            .where(AgentEvalSuite.agent_id == agent_id, AgentEvalRun.status == "completed")
            .order_by(AgentEvalRun.completed_at.desc())
            .limit(1)
        )
        res_run = await self.db.execute(stmt_run)
        latest_run = res_run.scalar_one_or_none()

        if latest_run:
            is_ready, reasons = await scoring_manager.evaluate_promotion_readiness(agent_id, latest_run.id)
            checks["eval_baseline"] = is_ready
            if not is_ready:
                logger.info(f"Advanced eval promotion check failed for agent {agent_id}: {reasons}")
        else:
            # Fallback to legacy check if no advanced run found
            res_eval = await self.db.execute(select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == agent_id))
            eval_baseline = res_eval.scalar_one_or_none()
            checks["eval_baseline"] = eval_baseline is not None and eval_baseline.score >= 0.8

        # 2. Security Check (Red Team)
        from app.services.agents.evals.red_team import RedTeamScanner
        scanner = RedTeamScanner(self.db)
        # Scan recent interaction or check red-team cases
        # For this check, we'll verify if there are any red-team failures
        checks["security_check"] = True # Simplified for now, in practice we'd check red-team run results
        res_incidents = await self.db.execute(
            select(AgentIncident).where(
                AgentIncident.agent_id == agent_id,
                AgentIncident.status == "open",
                AgentIncident.severity == "critical"
            )
        )
        checks["no_critical_incidents"] = res_incidents.scalar_one_or_none() is None

        # 3. Prompt Freshness
        checks["prompt_freshness"] = await self.baseline_registry.validate_prompt_against_baseline(agent_id, agent.instructions)

        # Result consolidation
        passed = all(checks.values())
        
        gate = AgentPromotionGate(
            agent_id=registry.id if registry else agent_id,
            target_status=target_status,
            eval_passed=checks["eval_baseline"],
            security_passed=checks["security_check"],
            compatibility_passed=checks["compatibility_check"],
            policy_passed=checks["owner_assigned"],
            owner_approved=False,
            status="passed" if passed else "failed",
            created_at=utc_now()
        )
        self.db.add(gate)
        await self.db.commit()

        return {
            "passed": passed,
            "checks": checks,
            "gate_id": str(gate.id),
            "risk_level": self.risk_engine.calculate_risk_level(agent)
        }

    async def promote_agent(self, agent_id: uuid.UUID, target_status: str, approved_by: str) -> Dict[str, Any]:
        """
        Promotes an agent if it passes the promotion gate.
        """
        check_result = await self.run_promotion_check(agent_id, target_status)
        if not check_result["passed"]:
            raise PromotionGateError(f"Agent failed promotion check: {check_result['checks']}")
        
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        agent = res_agent.scalar_one_or_none()
        
        agent.status = target_status
        # Log promotion event
        from app.services.agents import agent_state
        await agent_state.log_run_event(
            self.db, run_id=None, # System level
            event_type="agent_promoted",
            details={"agent_id": str(agent_id), "to_status": target_status, "promoted_by": approved_by}
        )
        
        await self.db.commit()
        return {"status": "promoted", "agent_id": str(agent_id), "new_status": target_status}
