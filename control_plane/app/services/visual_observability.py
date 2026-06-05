import logging
import os
import uuid
from datetime import datetime, timedelta, UTC
from statistics import mean
from typing import Any, Dict, List

from app.core.config import get_settings
from app.models.agent_workflows import AgentWorkflowEvent
from app.models.agents import (
    AgentIncident,
    AgentRun,
    AgentRunEvent,
    AgentRunStep,
)
from app.services.platform_slo import PlatformSLOService
from prometheus_client import REGISTRY
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

def sanitize_dict(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for k, v in data.items():
        if any(secret in k.lower() for secret in ["secret", "token", "password", "key", "credential", "auth"]):
            sanitized[k] = "********"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            sanitized[k] = v
    return sanitized

class VisualObservabilityService:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.settings = get_settings()

    def get_dashboard_links(self) -> List[Dict[str, str]]:
        base_url = os.getenv("GRAFANA_URL", "http://localhost:3001")
        return [
            {"name": "Platform Overview", "url": f"{base_url}/dashboards/platform-overview"},
            {"name": "Runtime Nodes", "url": f"{base_url}/dashboards/runtime-nodes"},
            {"name": "GPU Capacity", "url": f"{base_url}/dashboards/gpu-capacity"},
            {"name": "Queue and QoS", "url": f"{base_url}/dashboards/queue-qos"},
            {"name": "Provider Health", "url": f"{base_url}/dashboards/provider-health"},
            {"name": "Billing & Tokens", "url": f"{base_url}/dashboards/billing-tokens"},
            {"name": "Security & RBAC", "url": f"{base_url}/dashboards/security-rbac"},
            {"name": "SLO & Error Budget", "url": f"{base_url}/dashboards/slo-error-budget"},
        ]

    def get_metrics_derived(self) -> Dict[str, Any]:
        requests_total = self._counter_total("llm_requests_total")
        errors_total = self._counter_total("llm_request_errors_total")
        fallbacks_total = self._counter_total("llm_routing_fallbacks_total")
        decisions_total = self._counter_total("llm_routing_decisions_total")
        cache_hits_total = self._counter_total("llm_cache_hits_total")
        cache_misses_total = self._counter_total("llm_cache_misses_total")

        provider_health_scores = self._gauge_values("llm_provider_health_score")
        provider_reliability_score = mean(provider_health_scores) if provider_health_scores else 0.0
        if provider_reliability_score == 0.0 and requests_total > 0:
            provider_reliability_score = max(0.0, 1.0 - (errors_total / requests_total))

        fallback_rate = (fallbacks_total / decisions_total) if decisions_total > 0 else 0.0
        error_rate = (errors_total / requests_total) if requests_total > 0 else 0.0
        cache_hit_ratio = (cache_hits_total / (cache_hits_total + cache_misses_total)) if (cache_hits_total + cache_misses_total) > 0 else 0.0

        slo = PlatformSLOService().get_slo_report()
        health = PlatformSLOService().get_platform_health()

        return {
            "provider_reliability_score": round(provider_reliability_score, 4),
            "request_error_rate": round(error_rate, 4),
            "routing_fallback_rate": round(fallback_rate, 4),
            "cache_hit_ratio": round(cache_hit_ratio, 4),
            "total_requests": int(requests_total),
            "total_errors": int(errors_total),
            "total_routing_decisions": int(decisions_total),
            "slo_status": slo.get("api_availability", {}).get("status", "unknown"),
            "platform_status": health.get("status", "unknown"),
            "critical_issues": health.get("critical_issues", []),
        }

    async def get_error_budget(self) -> Dict[str, Any]:
        if not self.db:
            return {"status": "no_data", "message": "No database session configured."}

        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        
        try:
            # Total runs in the last 30 days
            res_total = await self.db.execute(
                select(func.count(AgentRun.id)).where(AgentRun.created_at >= thirty_days_ago)
            )
            total_runs = res_total.scalar() or 0

            # Failed runs in the last 30 days
            res_failed = await self.db.execute(
                select(func.count(AgentRun.id))
                .where(AgentRun.created_at >= thirty_days_ago)
                .where(AgentRun.status.in_(["failed", "error"]))
            )
            failed_runs = res_failed.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to query error budget: {e}")
            return {"status": "no_data", "message": f"Query error: {e}"}

        if total_runs == 0:
            return {
                "status": "no_data",
                "message": "No agent run data available in the last 30 days."
            }

        availability = ((total_runs - failed_runs) / total_runs) * 100
        slo_target = 99.9
        
        allowed_failures = total_runs * (1 - slo_target / 100.0)
        if allowed_failures > 0:
            remaining = max(0.0, ((allowed_failures - failed_runs) / allowed_failures) * 100.0)
        else:
            remaining = 0.0

        return {
            "slo_target": slo_target,
            "current_availability": round(availability, 4),
            "remaining_budget_percent": round(remaining, 2),
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "period_days": 30,
            "is_critical": remaining < 10.0
        }

    def _counter_total(self, metric_name: str) -> float:
        total = 0.0
        for family in REGISTRY.collect():
            if family.name != metric_name:
                continue
            for sample in family.samples:
                if sample.name == metric_name or sample.name == f"{metric_name}_total":
                    total += float(sample.value)
        return total

    def _gauge_values(self, metric_name: str) -> List[float]:
        values: List[float] = []
        for family in REGISTRY.collect():
            if family.name != metric_name:
                continue
            for sample in family.samples:
                if sample.name == metric_name:
                    values.append(float(sample.value))
        return values

    async def get_incident_timeline(self, limit: int = 50) -> Dict[str, Any]:
        if not self.db:
            return {"status": "no_data", "items": []}

        try:
            # Query incidents
            res_inc = await self.db.execute(
                select(AgentIncident).order_by(AgentIncident.created_at.desc()).limit(limit)
            )
            incidents = res_inc.scalars().all()

            # Query workflow events
            res_wf = await self.db.execute(
                select(AgentWorkflowEvent).order_by(AgentWorkflowEvent.created_at.desc()).limit(limit)
            )
            wf_events = res_wf.scalars().all()
        except Exception as e:
            logger.error(f"Failed to query incident timeline: {e}")
            return {"status": "no_data", "items": []}

        items = []
        for inc in incidents:
            items.append({
                "id": str(inc.id),
                "timestamp": inc.created_at.isoformat(),
                "type": "incident",
                "incident_type": inc.incident_type,
                "severity": inc.severity,
                "title": inc.title,
                "description": inc.description
            })
        
        for wf in wf_events:
            items.append({
                "id": str(wf.id),
                "timestamp": wf.created_at.isoformat(),
                "type": "workflow_event",
                "event_type": wf.event_type,
                "from_state": wf.from_state,
                "to_state": wf.to_state,
                "payload": sanitize_dict(wf.payload or {})
            })

        items.sort(key=lambda x: x["timestamp"], reverse=True)
        items = items[:limit]

        if not items:
            return {"status": "no_data", "items": []}

        return {"items": items}

    async def get_agent_run_timeline(self, run_id: uuid.UUID) -> Dict[str, Any]:
        if not self.db:
            return {"status": "no_data", "items": []}

        try:
            # Verify run exists
            run = await self.db.get(AgentRun, run_id)
            if not run:
                return {"status": "error", "message": "Agent run not found"}

            # Steps
            res_steps = await self.db.execute(
                select(AgentRunStep).where(AgentRunStep.run_id == run_id)
            )
            steps = res_steps.scalars().all()

            # Events
            res_events = await self.db.execute(
                select(AgentRunEvent).where(AgentRunEvent.run_id == run_id)
            )
            events = res_events.scalars().all()
        except Exception as e:
            logger.error(f"Failed to query agent run timeline: {e}")
            return {"status": "no_data", "items": []}

        items = []
        for s in steps:
            items.append({
                "id": str(s.id),
                "timestamp": s.created_at.isoformat() if s.created_at else None,
                "type": "step",
                "step_type": s.step_type,
                "status": s.status,
                "details": sanitize_dict(s.step_details or {})
            })
        
        for e in events:
            items.append({
                "id": str(e.id),
                "timestamp": e.created_at.isoformat() if e.created_at else None,
                "type": "event",
                "event_type": e.event_type,
                "details": sanitize_dict(e.event_details or {})
            })

        items.sort(key=lambda x: x["timestamp"] or "")

        if not items:
            return {"status": "no_data", "items": []}

        return {"run_id": str(run_id), "items": items}
