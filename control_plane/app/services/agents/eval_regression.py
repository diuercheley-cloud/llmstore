"""
Owner: agent-platform
Status: beta
"""

import logging
import uuid

from app.core.time import utc_now
from app.models.agents.agents import (
    AgentEvalBaseline,
    AgentEvalRegressionResult,
    AgentEvalResult,
    AgentEvalRun,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class EvalRegressionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_regression(
        self, agent_id: uuid.UUID, eval_run_id: uuid.UUID
    ) -> AgentEvalRegressionResult:
        # 1. Fetch current baseline
        res_base = await self.db.execute(
            select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == agent_id)
        )
        baseline = res_base.scalar_one_or_none()

        # 2. Fetch current eval run
        res_run = await self.db.execute(select(AgentEvalRun).where(AgentEvalRun.id == eval_run_id))
        eval_run = res_run.scalar_one_or_none()
        if not eval_run:
            raise ValueError(f"Eval run not found: {eval_run_id}")

        new_pass_rate = (
            eval_run.passed_count / eval_run.total_count if eval_run.total_count > 0 else 0.0
        )

        # Calculate new run average latency and total cost
        res_results = await self.db.execute(
            select(AgentEvalResult).where(AgentEvalResult.run_id == eval_run_id)
        )
        new_results = res_results.scalars().all()
        new_avg_latency = (
            sum(r.latency_ms for r in new_results if r.latency_ms is not None) / len(new_results)
            if new_results
            else 0.0
        )
        new_total_cost = sum(r.total_cost_brl for r in new_results if r.total_cost_brl is not None)

        if not baseline:
            # No baseline exists yet. This cannot be a regression, so regression_detected = False and passed = True.
            # (First run will become the baseline)
            regression_result = AgentEvalRegressionResult(
                agent_id=agent_id,
                eval_run_id=eval_run_id,
                baseline_run_id=None,
                passed=True,
                regression_detected=False,
                metric_diffs={
                    "note": "No baseline exists for comparison.",
                    "pass_rate_diff": 0.0,
                    "avg_latency_diff": 0.0,
                    "total_cost_diff": 0.0,
                },
                created_at=utc_now(),
            )
            self.db.add(regression_result)
            await self.db.commit()
            await self.db.refresh(regression_result)
            return regression_result

        # Fetch baseline run metrics
        res_base_run = await self.db.execute(
            select(AgentEvalRun).where(AgentEvalRun.id == baseline.run_id)
        )
        base_run = res_base_run.scalar_one_or_none()

        base_pass_rate = baseline.pass_rate
        base_avg_latency = 0.0
        base_total_cost = 0.0

        if base_run:
            res_base_results = await self.db.execute(
                select(AgentEvalResult).where(AgentEvalResult.run_id == baseline.run_id)
            )
            base_results = res_base_results.scalars().all()
            base_avg_latency = (
                sum(r.latency_ms for r in base_results if r.latency_ms is not None)
                / len(base_results)
                if base_results
                else 0.0
            )
            base_total_cost = sum(
                r.total_cost_brl for r in base_results if r.total_cost_brl is not None
            )

        # Detect regression
        regression_detected = False
        reasons = []

        # Pass rate regression: strict check
        pass_rate_diff = new_pass_rate - base_pass_rate
        if pass_rate_diff < -0.01:  # 1% margin
            regression_detected = True
            reasons.append(f"Pass rate decreased from {base_pass_rate:.2%} to {new_pass_rate:.2%}")

        # Latency regression
        latency_diff = new_avg_latency - base_avg_latency
        if base_avg_latency > 0 and latency_diff > 5000:  # 5s deterioration
            # We could block here if needed
            pass

        # Store metric diffs
        metric_diffs = {
            "pass_rate_diff": pass_rate_diff,
            "avg_latency_diff": latency_diff,
            "total_cost_diff": new_total_cost - base_total_cost,
            "reasons": reasons,
            "baseline_pass_rate": base_pass_rate,
            "new_pass_rate": new_pass_rate,
        }

        # Gate passes regression check if no regression detected
        passed = not regression_detected

        regression_result = AgentEvalRegressionResult(
            agent_id=agent_id,
            eval_run_id=eval_run_id,
            baseline_run_id=baseline.run_id,
            passed=passed,
            regression_detected=regression_detected,
            metric_diffs=metric_diffs,
            created_at=utc_now(),
        )
        self.db.add(regression_result)
        await self.db.commit()
        await self.db.refresh(regression_result)
        return regression_result
