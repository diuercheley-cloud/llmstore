import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.models.agents.agents import (
    AgentDefinition,
    AgentPolicyDecision,
    AgentRun,
    AgentTool,
    AgentToolInvocation,
)
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agent_analytics")


class AgentAnalyticsService:
    @classmethod
    async def get_overview(
        cls, db: AsyncSession, tenant_id: str, start_time: datetime, end_time: datetime
    ) -> dict[str, Any]:
        """Gets high-level metrics overview for all agents of a tenant."""
        # 1. Fetch total counts, costs, tokens, memory reads, wait times
        stmt_summary = select(
            func.count(AgentRun.id).label("total_runs"),
            func.sum(case((AgentRun.status == "completed", 1), else_=0)).label("completed_runs"),
            func.sum(case((AgentRun.status == "failed", 1), else_=0)).label("failed_runs"),
            func.sum(AgentRun.estimated_cost_brl).label("total_cost"),
            func.sum(AgentRun.total_tokens).label("total_tokens"),
            func.sum(AgentRun.tool_calls_count).label("total_tool_calls"),
            func.sum(AgentRun.memory_reads_count).label("total_memory_reads"),
            func.sum(AgentRun.approval_wait_seconds).label("total_wait_time"),
        ).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time,
            )
        )
        res_summary = await db.execute(stmt_summary)
        summary = res_summary.one()

        total_runs = summary.total_runs or 0
        if total_runs == 0:
            return {
                "status": "no_data",
                "message": "No run data available for this tenant.",
                "total_runs": 0,
                "agents": [],
            }

        completed = summary.completed_runs or 0
        failed = summary.failed_runs or 0
        success_rate = completed / total_runs if total_runs > 0 else 0.0
        failure_rate = failed / total_runs if total_runs > 0 else 0.0

        # Policy denials count
        stmt_denials = select(func.count(AgentPolicyDecision.id)).where(
            and_(
                AgentPolicyDecision.tenant_id == tenant_id,
                AgentPolicyDecision.result == "deny",
                AgentPolicyDecision.created_at >= start_time,
                AgentPolicyDecision.created_at <= end_time,
            )
        )
        res_denials = await db.execute(stmt_denials)
        policy_denials = res_denials.scalar_one() or 0

        # 2. Get list of agents with individual summary
        stmt_agents = (
            select(
                AgentDefinition.id,
                AgentDefinition.name,
                func.count(AgentRun.id).label("agent_runs"),
                func.sum(case((AgentRun.status == "completed", 1), else_=0)).label(
                    "agent_completed"
                ),
                func.sum(AgentRun.estimated_cost_brl).label("agent_cost"),
            )
            .join(AgentRun, AgentDefinition.id == AgentRun.agent_id)
            .where(
                and_(
                    AgentRun.tenant_id == tenant_id,
                    AgentRun.started_at >= start_time,
                    AgentRun.started_at <= end_time,
                )
            )
            .group_by(AgentDefinition.id, AgentDefinition.name)
        )
        res_agents = await db.execute(stmt_agents)

        agents_list = []
        for row in res_agents.all():
            a_runs = row.agent_runs or 0
            a_comp = row.agent_completed or 0
            agents_list.append(
                {
                    "agent_id": str(row.id),
                    "name": row.name,
                    "runs": a_runs,
                    "success_rate": a_comp / a_runs if a_runs > 0 else 0.0,
                    "total_cost_brl": float(row.agent_cost or 0.0),
                }
            )

        return {
            "status": "success",
            "total_runs": total_runs,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "total_cost_brl": float(summary.total_cost or 0.0),
            "total_tokens": int(summary.total_tokens or 0),
            "total_tool_calls": int(summary.total_tool_calls or 0),
            "total_memory_reads": int(summary.total_memory_reads or 0),
            "approval_wait_time_seconds": float(summary.total_wait_time or 0.0),
            "policy_denials": policy_denials,
            "agents": agents_list,
        }

    @classmethod
    async def get_agent_metrics(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Gets detailed metrics for a single agent, including latency percentiles."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return {"status": "no_data", "message": "Invalid agent_id format."}

        # Verify agent exists and belongs to tenant
        stmt_def = select(AgentDefinition).where(
            AgentDefinition.id == agent_uuid, AgentDefinition.tenant_id == tenant_id
        )
        res_def = await db.execute(stmt_def)
        agent = res_def.scalar_one_or_none()
        if not agent:
            return {"status": "no_data", "message": "Agent not found or tenant mismatch."}

        # Query all runs for this agent to calculate details and in-memory percentiles
        stmt_runs = select(
            AgentRun.status,
            AgentRun.started_at,
            AgentRun.completed_at,
            AgentRun.estimated_cost_brl,
            AgentRun.total_tokens,
            AgentRun.tool_calls_count,
            AgentRun.memory_reads_count,
            AgentRun.approval_wait_seconds,
        ).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.agent_id == agent_uuid,
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time,
            )
        )
        res_runs = await db.execute(stmt_runs)
        runs = res_runs.all()

        total_runs = len(runs)
        if total_runs == 0:
            return {
                "status": "no_data",
                "message": "No runs found for this agent in the specified time range.",
            }

        completed = 0
        failed = 0
        total_cost = 0.0
        total_tokens = 0
        total_tool_calls = 0
        total_memory_reads = 0
        total_wait_time = 0.0
        durations = []

        for r in runs:
            if r.status == "completed":
                completed += 1
            elif r.status == "failed":
                failed += 1

            total_cost += r.estimated_cost_brl or 0.0
            total_tokens += r.total_tokens or 0
            total_tool_calls += r.tool_calls_count or 0
            total_memory_reads += r.memory_reads_count or 0
            total_wait_time += r.approval_wait_seconds or 0.0

            if r.started_at and r.completed_at:
                durations.append((r.completed_at - r.started_at).total_seconds())

        # Compute percentiles
        p50, p95, p99 = 0.0, 0.0, 0.0
        if durations:
            durations.sort()
            n = len(durations)
            p50 = durations[int(n * 0.50)]
            p95 = durations[int(n * 0.95)]
            p99 = durations[int(n * 0.99)]

        # Policy denials count
        stmt_denials = select(func.count(AgentPolicyDecision.id)).where(
            and_(
                AgentPolicyDecision.tenant_id == tenant_id,
                AgentPolicyDecision.agent_id == agent_uuid,
                AgentPolicyDecision.result == "deny",
                AgentPolicyDecision.created_at >= start_time,
                AgentPolicyDecision.created_at <= end_time,
            )
        )
        res_denials = await db.execute(stmt_denials)
        policy_denials = res_denials.scalar_one() or 0

        return {
            "status": "success",
            "agent_id": agent_id,
            "name": agent.name,
            "total_runs": total_runs,
            "success_rate": completed / total_runs if total_runs > 0 else 0.0,
            "failure_rate": failed / total_runs if total_runs > 0 else 0.0,
            "p50_latency_seconds": p50,
            "p95_latency_seconds": p95,
            "p99_latency_seconds": p99,
            "average_cost_per_run_brl": total_cost / total_runs if total_runs > 0 else 0.0,
            "total_cost_brl": total_cost,
            "total_tokens": total_tokens,
            "average_tokens_per_run": total_tokens / total_runs if total_runs > 0 else 0.0,
            "total_tool_calls": total_tool_calls,
            "average_tool_calls_per_run": total_tool_calls / total_runs if total_runs > 0 else 0.0,
            "total_memory_reads": total_memory_reads,
            "average_memory_reads_per_run": total_memory_reads / total_runs
            if total_runs > 0
            else 0.0,
            "approval_wait_time_seconds": total_wait_time,
            "average_approval_wait_time_seconds": total_wait_time / total_runs
            if total_runs > 0
            else 0.0,
            "policy_denials": policy_denials,
        }

    @classmethod
    async def get_cost_trend(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "daily",  # daily, weekly, monthly
    ) -> dict[str, Any]:
        """Gets aggregated cost trend points."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return {"status": "no_data", "message": "Invalid agent_id format."}

        stmt = select(AgentRun.started_at, AgentRun.estimated_cost_brl).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.agent_id == agent_uuid,
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time,
            )
        )
        res = await db.execute(stmt)
        runs = res.all()

        if not runs:
            return {"status": "no_data", "trend": []}

        # Perform Python grouping
        groups = {}
        for r in runs:
            dt = r.started_at
            if granularity == "monthly":
                key = dt.strftime("%Y-%m")
            elif granularity == "weekly":
                # Start date of the week (Monday)
                start_of_week = dt.date() - timedelta(days=dt.weekday())
                key = start_of_week.strftime("%Y-%m-%d")
            else:
                key = dt.strftime("%Y-%m-%d")

            if key not in groups:
                groups[key] = {"cost": 0.0, "runs": 0}
            groups[key]["cost"] += r.estimated_cost_brl or 0.0
            groups[key]["runs"] += 1

        trend_points = []
        for k in sorted(groups.keys()):
            trend_points.append(
                {
                    "period": k,
                    "total_cost_brl": float(groups[k]["cost"]),
                    "run_count": groups[k]["runs"],
                    "average_cost_brl": float(groups[k]["cost"] / groups[k]["runs"])
                    if groups[k]["runs"] > 0
                    else 0.0,
                }
            )

        return {"status": "success", "trend": trend_points}

    @classmethod
    async def get_latency_trend(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "daily",
    ) -> dict[str, Any]:
        """Gets aggregated latency trend points with percentiles."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return {"status": "no_data", "message": "Invalid agent_id format."}

        stmt = select(AgentRun.started_at, AgentRun.completed_at).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.agent_id == agent_uuid,
                AgentRun.status == "completed",
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time,
            )
        )
        res = await db.execute(stmt)
        runs = res.all()

        if not runs:
            return {"status": "no_data", "trend": []}

        # Perform Python grouping
        groups = {}
        for r in runs:
            if not r.started_at or not r.completed_at:
                continue
            dt = r.started_at
            duration = (r.completed_at - r.started_at).total_seconds()

            if granularity == "monthly":
                key = dt.strftime("%Y-%m")
            elif granularity == "weekly":
                start_of_week = dt.date() - timedelta(days=dt.weekday())
                key = start_of_week.strftime("%Y-%m-%d")
            else:
                key = dt.strftime("%Y-%m-%d")

            if key not in groups:
                groups[key] = []
            groups[key].append(duration)

        trend_points = []
        for k in sorted(groups.keys()):
            durations = groups[k]
            durations.sort()
            n = len(durations)
            p50 = durations[int(n * 0.50)]
            p95 = durations[int(n * 0.95)]
            p99 = durations[int(n * 0.99)]
            trend_points.append(
                {
                    "period": k,
                    "p50_latency_seconds": p50,
                    "p95_latency_seconds": p95,
                    "p99_latency_seconds": p99,
                    "run_count": n,
                }
            )

        return {"status": "success", "trend": trend_points}

    @classmethod
    async def get_tools_usage(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Gets tool invocation metrics breakdown for a single agent."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return {"status": "no_data", "message": "Invalid agent_id format."}

        stmt = (
            select(
                AgentTool.name,
                func.count(AgentToolInvocation.id).label("calls"),
                func.sum(case((AgentToolInvocation.status == "failed", 1), else_=0)).label(
                    "failures"
                ),
                func.avg(AgentToolInvocation.latency_ms).label("avg_latency"),
            )
            .join(AgentToolInvocation, AgentTool.id == AgentToolInvocation.agent_tool_id)
            .join(AgentRun, AgentToolInvocation.run_id == AgentRun.id)
            .where(
                and_(
                    AgentRun.tenant_id == tenant_id,
                    AgentRun.agent_id == agent_uuid,
                    AgentRun.started_at >= start_time,
                    AgentRun.started_at <= end_time,
                )
            )
            .group_by(AgentTool.name)
        )

        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return {"status": "no_data", "tools": []}

        tools_usage = []
        for row in rows:
            calls = row.calls or 0
            failures = row.failures or 0
            tools_usage.append(
                {
                    "tool_name": row.name,
                    "total_calls": calls,
                    "failure_rate": failures / calls if calls > 0 else 0.0,
                    "average_latency_ms": float(row.avg_latency or 0.0),
                }
            )

        return {"status": "success", "tools": tools_usage}
