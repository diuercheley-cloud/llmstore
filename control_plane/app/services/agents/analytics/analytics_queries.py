# Owner: agent-platform
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.agents import AgentRun, AgentRunMetrics, AgentRunCosts, AgentPolicyDecision, AgentEvalResult

class AnalyticsQueries:
    """
    Specialized queries for agent analytics.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_run_success_rate(self, tenant_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        stmt = select(
            AgentRun.status,
            func.count(AgentRun.id).label("count")
        ).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time
            )
        ).group_by(AgentRun.status)
        
        res = await self.db.execute(stmt)
        data = {row.status: row.count for row in res.all()}
        
        total = sum(data.values())
        success = data.get("completed", 0)
        
        return {
            "total": total,
            "success_rate": (success / total) if total > 0 else 0,
            "distribution": data
        }

    async def get_cost_and_tokens(self, tenant_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        stmt = select(
            func.sum(AgentRunCosts.estimated_cost_brl).label("total_cost"),
            func.sum(AgentRunCosts.prompt_tokens + AgentRunCosts.completion_tokens).label("total_tokens")
        ).where(
            and_(
                AgentRunCosts.tenant_id == tenant_id,
                AgentRunCosts.created_at >= start_time,
                AgentRunCosts.created_at <= end_time
            )
        )
        
        res = await self.db.execute(stmt)
        stats = res.one()
        
        return {
            "total_cost_brl": float(stats.total_cost or 0.0),
            "total_tokens": int(stats.total_tokens or 0)
        }

    async def get_tool_metrics(self, tenant_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        stmt = select(
            func.sum(AgentRunMetrics.total_tool_calls).label("total_calls"),
            func.sum(AgentRunMetrics.total_tool_errors).label("total_errors")
        ).join(AgentRun, AgentRunMetrics.run_id == AgentRun.id).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentRun.started_at >= start_time,
                AgentRun.started_at <= end_time
            )
        )
        
        res = await self.db.execute(stmt)
        stats = res.one()
        
        total = int(stats.total_calls or 0)
        errors = int(stats.total_errors or 0)
        
        return {
            "total_tool_calls": total,
            "tool_failure_rate": (errors / total) if total > 0 else 0
        }

    async def get_policy_denials(self, tenant_id: str, start_time: datetime, end_time: datetime) -> int:
        stmt = select(func.count(AgentPolicyDecision.id)).where(
            and_(
                AgentPolicyDecision.tenant_id == tenant_id,
                AgentPolicyDecision.result == "deny",
                AgentPolicyDecision.created_at >= start_time,
                AgentPolicyDecision.created_at <= end_time
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def get_eval_pass_rate(self, tenant_id: str, start_time: datetime, end_time: datetime) -> float:
        stmt = select(
            func.avg(func.cast(AgentEvalResult.passed, func.Integer))
        ).join(AgentRun, AgentEvalResult.run_id_ref == AgentRun.id).where(
            and_(
                AgentRun.tenant_id == tenant_id,
                AgentEvalResult.created_at >= start_time,
                AgentEvalResult.created_at <= end_time
            )
        )
        res = await self.db.execute(stmt)
        return float(res.scalar_one() or 0.0)
