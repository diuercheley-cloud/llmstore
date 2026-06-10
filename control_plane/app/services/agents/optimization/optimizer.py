import logging
import uuid
from typing import List, Tuple

from app.core.config import get_settings
from app.models.agents.agent_optimization import (
    AgentOptimizationCandidate,
    AgentOptimizationExperiment,
    AgentPolicyCandidate,
    AgentPromptCandidate,
    AgentToolSelectionCandidate,
)
from app.models.agents.agents import AgentDefinition, AgentEvalFailure, AgentRun
from app.services.agents.optimization.policy_optimizer import PolicyOptimizer
from app.services.agents.optimization.prompt_optimizer import PromptOptimizer
from app.services.agents.optimization.tool_selection_optimizer import ToolSelectionOptimizer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AgentOptimizerCoordinator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.prompt_opt = PromptOptimizer()
        self.tool_opt = ToolSelectionOptimizer()
        self.policy_opt = PolicyOptimizer()

    async def run_optimization_experiment(
        self, tenant_id: str, agent_id: uuid.UUID
    ) -> Tuple[AgentOptimizationExperiment, List[AgentOptimizationCandidate]]:
        """
        Runs an auto-optimization experiment:
        1. Collects failed evals/runs.
        2. Generates candidate prompts, tool selections, and policies.
        3. Creates the database entries.
        """
        settings = get_settings()
        if not settings.agent_auto_optimization_enabled or not settings.agent_dspy_optimizer_enabled:
            raise PermissionError("Auto-optimization / DSPy optimizer is disabled by feature flag.")

        # 1. Fetch active AgentDefinition
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        agent = res_agent.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent Definition with ID {agent_id} not found.")

        # 2. Collect failures
        res_failures = await self.db.execute(
            select(AgentEvalFailure)
            .where(AgentEvalFailure.agent_id == agent_id)
            .order_by(AgentEvalFailure.created_at.desc())
            .limit(10)
        )
        failures = list(res_failures.scalars().all())

        # Collect failed runs as well
        res_runs = await self.db.execute(
            select(AgentRun)
            .where(AgentRun.agent_id == agent_id, AgentRun.status == "failed")
            .order_by(AgentRun.started_at.desc())
            .limit(10)
        )
        failed_runs = list(res_runs.scalars().all())

        # Adapt run failures to AgentEvalFailure format for input to optimizers
        all_failures = list(failures)
        for r in failed_runs:
            # simple mock representation for optimizer consumption
            all_failures.append(
                AgentEvalFailure(
                    agent_id=agent_id,
                    run_id=r.id,
                    failure_type="tool_error" if r.tool_calls_count > 0 else "execution_failure",
                    details={"input_text": r.input_text, "steps": r.total_steps},
                )
            )

        # 3. Create Experiment
        experiment = AgentOptimizationExperiment(
            tenant_id=tenant_id,
            agent_id=agent_id,
            status="running",
            metrics_baseline={
                "instructions": agent.instructions,
                "allowed_tools": agent.allowed_tools or [],
                "policy_id": agent.policy_id
            }
        )
        self.db.add(experiment)
        await self.db.flush()

        candidates = []

        # A. Prompt Candidate
        opt_prompt_text = self.prompt_opt.optimize_prompt(agent.instructions, all_failures)
        p_cand = AgentOptimizationCandidate(
            experiment_id=experiment.id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            candidate_type="prompt",
            status="pending"
        )
        self.db.add(p_cand)
        await self.db.flush()

        prompt_detail = AgentPromptCandidate(
            candidate_id=p_cand.id,
            prompt_text=opt_prompt_text,
            improved_instructions=f"Optimized instructions based on {len(all_failures)} failure logs."
        )
        self.db.add(prompt_detail)
        candidates.append(p_cand)

        # B. Tool Selection Candidate
        opt_tools = self.tool_opt.optimize_tool_selection(agent.allowed_tools or [], all_failures)
        t_cand = AgentOptimizationCandidate(
            experiment_id=experiment.id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            candidate_type="tool_selection",
            status="pending"
        )
        self.db.add(t_cand)
        await self.db.flush()

        tool_detail = AgentToolSelectionCandidate(
            candidate_id=t_cand.id,
            allowed_tools=opt_tools
        )
        self.db.add(tool_detail)
        candidates.append(t_cand)

        # C. Policy Candidate
        # Simulate loading current policy rules
        opt_rules = self.policy_opt.optimize_policy({}, all_failures)
        pol_cand = AgentOptimizationCandidate(
            experiment_id=experiment.id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            candidate_type="policy",
            status="pending"
        )
        self.db.add(pol_cand)
        await self.db.flush()

        policy_detail = AgentPolicyCandidate(
            candidate_id=pol_cand.id,
            policy_rules=opt_rules
        )
        self.db.add(policy_detail)
        candidates.append(pol_cand)

        experiment.status = "completed"
        await self.db.flush()

        return experiment, candidates
