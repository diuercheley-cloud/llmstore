import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.config import get_settings

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

    async def get_error_budget(self) -> Dict[str, Any]:
        # Synthetic calculation for demonstration
        # In a real scenario, this would query Prometheus or the local events DB
        return {
            "slo_target": 99.9,
            "current_availability": 99.95,
            "remaining_budget_percent": 85.0,
            "burn_rate": 1.2,
            "period_days": 30,
            "is_critical": False
        }

    async def get_incident_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        # This would aggregate from multiple tables: security_events, audit_logs, etc.
        # Returning a mock timeline for now
        now = datetime.utcnow()
        return [
            {
                "id": str(uuid.uuid4()),
                "timestamp": (now - timedelta(minutes=15)).isoformat(),
                "type": "provider_failure",
                "severity": "high",
                "title": "OpenAI Provider Timeout Spike",
                "description": "Detected 5% increase in timeout errors from OpenAI backend."
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "type": "rbac_denial",
                "severity": "medium",
                "title": "Repeated RBAC Denial",
                "description": "Multiple unauthorized attempts to access /admin/billing from IP 10.0.0.45."
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": (now - timedelta(hours=5)).isoformat(),
                "type": "gpu_pressure",
                "severity": "low",
                "title": "GPU Memory Pressure",
                "description": "Node 'worker-01' reached 92% GPU memory utilization."
            }
        ]

    def get_metrics_derived(self) -> Dict[str, Any]:
        return {
            "availability_window_24h": 0.9998,
            "error_budget_remaining": 0.85,
            "burn_rate": 1.1,
            "provider_reliability_score": 0.96,
            "queue_saturation_ratio": 0.35,
            "cost_per_successful_request": 0.0024,
            "token_accuracy_ratio": 0.999
        }
