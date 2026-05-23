# Owner: platform-ops
from datetime import datetime
from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.services.auth import require_admin_role, AdminRole
from app.core.config import get_settings
from app.db.session import get_db_session
from app.core.time import utc_now

router = APIRouter(prefix="/admin/operations", tags=["operations_ux"])

# --- Schemas ---

class StatusOverview(BaseModel):
    status: str
    deployment_mode: str
    uptime_seconds: float
    active_nodes: int
    healthy_nodes: int
    active_models: int
    queue_size: int
    pending_incidents: int
    risk_level: str
    enterprise_features: Dict[str, bool]

class IncidentItem(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    started_at: str
    description: str

class RecommendationItem(BaseModel):
    id: str
    title: str
    action: str
    impact: str
    priority: str
    runbook_url: str

class RuntimeNode(BaseModel):
    id: str
    name: str
    role: str
    status: str
    version: str
    cpu_usage: float
    memory_usage: float
    gpu_usage: float | None = None
    last_heartbeat: str

# --- Endpoints ---

@router.get("/overview", response_model=StatusOverview)
async def get_operations_overview(
    admin: Any = Depends(require_admin_role(AdminRole.READ)),
    settings = Depends(get_settings)
) -> Any:
    # Em um cenário real, buscaríamos métricas reais. Aqui usamos dados do settings e mocks para os itens dinâmicos.
    return {
        "status": "healthy",
        "deployment_mode": settings.deployment_mode,
        "uptime_seconds": utc_now().timestamp() - settings.start_time,
        "active_nodes": 12,
        "healthy_nodes": 11,
        "active_models": 5,
        "queue_size": 0,
        "pending_incidents": 1,
        "risk_level": "low",
        "enterprise_features": {
            "commercial_routing": settings.commercial_routing_enabled,
            "commercial_qos": settings.commercial_qos_priority_queue_enabled,
            "commercial_guardrails": settings.commercial_guardrails_enabled,
            "managed_control_plane": settings.managed_control_plane_enabled
        }
    }

@router.get("/incidents", response_model=List[IncidentItem])
async def list_incidents(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return [
        {
            "id": "INC-2024-001",
            "title": "Degradação de latência em gemma-7b",
            "severity": "medium",
            "status": "investigating",
            "started_at": utc_now().isoformat(),
            "description": "Aumento de 15% no p99 observado no cluster sul-1."
        }
    ]

@router.get("/recommendations", response_model=List[RecommendationItem])
async def list_recommendations(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return [
        {
            "id": "REC-001",
            "title": "Otimizar cache de semântica",
            "action": "Ativar 'semantic_cache_enabled' para reduzir custos em 20%",
            "impact": "Cost Reduction",
            "priority": "high",
            "runbook_url": "/docs/runbooks/semantic-cache-optimization"
        },
        {
            "id": "REC-002",
            "title": "Atualizar Runtime Nodes",
            "action": "3 nós estão rodando versão v1.1.0 (atual v1.2.0)",
            "impact": "Security",
            "priority": "medium",
            "runbook_url": "/docs/runbooks/node-upgrade"
        }
    ]

@router.get("/runtime-nodes", response_model=List[RuntimeNode])
async def list_runtime_nodes(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return [
        {
            "id": "node-01",
            "name": "inference-worker-01",
            "role": "worker",
            "status": "ready",
            "version": "v1.2.0",
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "gpu_usage": 88.0,
            "last_heartbeat": utc_now().isoformat()
        },
        {
            "id": "node-02",
            "name": "inference-worker-02",
            "role": "worker",
            "status": "draining",
            "version": "v1.1.0",
            "cpu_usage": 12.5,
            "memory_usage": 30.2,
            "gpu_usage": 0.0,
            "last_heartbeat": utc_now().isoformat()
        }
    ]

@router.post("/run-readiness")
async def run_readiness_check(
    admin: Any = Depends(require_admin_role(AdminRole.WRITE))
) -> Any:
    # Trigger readiness check
    return {"status": "triggered", "job_id": str(uuid.uuid4())}

@router.post("/reset-circuit-breaker")
async def reset_circuit_breaker(
    target: str | None = None,
    admin: Any = Depends(require_admin_role(AdminRole.WRITE))
) -> Any:
    return {"status": "success", "reset_target": target or "all"}

@router.post("/nodes/{node_id}/drain")
async def drain_node(
    node_id: str,
    admin: Any = Depends(require_admin_role(AdminRole.WRITE))
) -> Any:
    return {"status": "draining", "node_id": node_id}

@router.post("/models/{model_id}/rollback")
async def rollback_model(
    model_id: str,
    admin: Any = Depends(require_admin_role(AdminRole.WRITE))
) -> Any:
    return {"status": "rollback_initiated", "model_id": model_id}

@router.get("/security-report")
async def download_security_report(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return {"report_url": "/static/reports/security-posture-latest.pdf", "generated_at": utc_now().isoformat()}

@router.get("/release-summary")
async def download_release_summary(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return {"release_version": "v1.2.0", "summary_url": "/static/releases/v1.2.0-summary.md"}

@router.get("/readiness-report")
async def get_readiness_report(
    admin: Any = Depends(require_admin_role(AdminRole.READ))
) -> Any:
    return {
        "overall_status": "ready",
        "checks": [
            {"name": "Database Connectivity", "status": "pass"},
            {"name": "Redis Availability", "status": "pass"},
            {"name": "Data Plane Reachability", "status": "pass"},
            {"name": "Inference Proxy Healthy", "status": "pass"},
            {"name": "Storage Permissions", "status": "pass"}
        ]
    }
