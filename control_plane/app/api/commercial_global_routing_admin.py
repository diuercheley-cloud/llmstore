# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from app.services.auth import require_admin
from app.services.routing import commercial_global_router
from app.services.routing.commercial_analytics import audit_log
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    return await commercial_global_router.get_global_router_overview(db)


@router.get("/recommendations")
async def get_recommendations(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    return await commercial_global_router.generate_cluster_recommendations(db)


@router.post("/simulate")
async def simulate_route(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    tenant_id = payload.get("tenant_id")
    provider = payload.get("provider")
    model = payload.get("model")
    region_preference = payload.get("region_preference")
    estimated_tokens = int(payload.get("estimated_tokens") or 0)

    result = await commercial_global_router.simulate_global_route(
        db,
        tenant_id=tenant_id,
        provider=provider,
        model=model,
        region_preference=region_preference,
        estimated_tokens=estimated_tokens,
    )

    recommended = result.get("recommended_cluster")
    recommended_id = recommended.get("cluster_id") if recommended else None

    # Audit log
    await audit_log(
        db,
        event_type="global_route_simulated",
        client_id="admin",
        details={
            "tenant_id": tenant_id,
            "provider": provider,
            "model": model,
            "region_preference": region_preference,
            "recommended_cluster": recommended_id,
        },
    )

    # Register rejections in audit
    for rejected in result.get("rejected_clusters", []):
        await audit_log(
            db,
            event_type="cluster_rejected",
            client_id="admin",
            details={
                "cluster_id": rejected["cluster_id"],
                "reason": rejected["reason"],
                "message": rejected["message"],
            },
        )

    return result


@router.get("/export")
async def export_routing(
    format: str = Query("json", pattern="^(json|csv|html)$"),
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> Any:
    data = await commercial_global_router.get_global_router_overview(db)

    if format == "csv":
        content = commercial_global_router.export_routing_csv(data)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=global_routing.csv"},
        )

    if format == "html":
        content = commercial_global_router.export_routing_html(data)
        return Response(content=content, media_type="text/html")

    return data


# --- Governed Global Routing Policy Support ---
import json
import uuid

from app.models.commercial.global_routing_policy import GlobalRoutingPolicyVersion
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select


class PolicySimulateRequest(BaseModel):
    policy_json: dict[str, Any]
    tenant_id: str | None = None
    provider: str | None = None
    model: str | None = None
    region_preference: str | None = None
    estimated_tokens: int = 0


class PolicyDraftRequest(BaseModel):
    policy_json: dict[str, Any]
    created_by: str | None = "admin"


def validate_policy_json(policy_dict: dict[str, Any]) -> None:
    weight_fields = [
        "commercial_global_routing_margin_weight",
        "commercial_global_routing_latency_weight",
        "commercial_global_routing_health_weight",
        "commercial_global_routing_region_weight",
        "commercial_global_routing_priority_weight",
    ]

    # Check weights exist and are numbers
    for field in weight_fields:
        if field not in policy_dict:
            raise ValueError(f"Missing required field: {field}")
        val = policy_dict[field]
        if not isinstance(val, (int, float)):
            raise ValueError(f"{field} must be a number")
        if val < 0.0 or val > 1.0:
            raise ValueError(f"{field} must be between 0.0 and 1.0")

    total_weight = sum(policy_dict[field] for field in weight_fields)
    if not (0.99 <= total_weight <= 1.01):
        raise ValueError(f"Sum of weights must be 1.0, got {total_weight}")

    bool_fields = [
        "commercial_global_routing_enabled",
        "commercial_global_routing_require_healthy_cluster",
        "commercial_global_routing_allow_cross_region",
    ]
    for field in bool_fields:
        if field in policy_dict and not isinstance(policy_dict[field], bool):
            raise ValueError(f"{field} must be a boolean")

    if "commercial_global_routing_mode" in policy_dict:
        mode = policy_dict["commercial_global_routing_mode"]
        if not isinstance(mode, str):
            raise ValueError("commercial_global_routing_mode must be a string")

    if "commercial_global_routing_max_latency_ms" in policy_dict:
        lat = policy_dict["commercial_global_routing_max_latency_ms"]
        if not isinstance(lat, (int, float)) or lat <= 0:
            raise ValueError("commercial_global_routing_max_latency_ms must be a positive number")


@router.post("/policies/simulate")
async def simulate_policy(
    payload: PolicySimulateRequest,
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    try:
        validate_policy_json(payload.policy_json)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.core.config import get_settings
    from app.services.routing.commercial_global_router import OverriddenSettings

    cfg = get_settings()
    overridden_cfg = OverriddenSettings(cfg, payload.policy_json)

    result = await commercial_global_router.simulate_global_route(
        db,
        tenant_id=payload.tenant_id,
        provider=payload.provider,
        model=payload.model,
        region_preference=payload.region_preference,
        estimated_tokens=payload.estimated_tokens,
        settings=overridden_cfg,
    )

    await audit_log(
        db,
        event_type="global_routing_policy_simulated",
        client_id="admin",
        details={
            "proposed_policy": payload.policy_json,
            "tenant_id": payload.tenant_id,
            "provider": payload.provider,
            "model": payload.model,
            "region_preference": payload.region_preference,
        },
    )
    return result


@router.post("/policies/draft")
async def create_draft(
    payload: PolicyDraftRequest,
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(func.max(GlobalRoutingPolicyVersion.version))
    res = await db.execute(stmt)
    max_version = res.scalar() or 0
    new_version = max_version + 1

    draft = GlobalRoutingPolicyVersion(
        version=new_version,
        policy_json=json.dumps(payload.policy_json),
        created_by=payload.created_by or "admin",
        status="draft",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return {
        "id": str(draft.id),
        "version": draft.version,
        "policy_json": payload.policy_json,
        "created_by": draft.created_by,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "status": draft.status,
        "previous_version_id": str(draft.previous_version_id)
        if draft.previous_version_id
        else None,
    }


@router.post("/policies/{policy_id}/activate")
async def activate_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    try:
        policy_uuid = uuid.UUID(policy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid policy UUID format")

    stmt = select(GlobalRoutingPolicyVersion).where(GlobalRoutingPolicyVersion.id == policy_uuid)
    res = await db.execute(stmt)
    policy = res.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy version not found")

    try:
        policy_dict = json.loads(policy.policy_json)
        validate_policy_json(policy_dict)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid policy content: {str(e)}")

    stmt_active = select(GlobalRoutingPolicyVersion).where(
        GlobalRoutingPolicyVersion.status == "active"
    )
    res_active = await db.execute(stmt_active)
    current_active = res_active.scalars().first()

    previous_version_id = current_active.id if current_active else None
    if current_active:
        current_active.status = "rolled_back"
        db.add(current_active)

    policy.status = "active"
    policy.previous_version_id = previous_version_id
    db.add(policy)

    await db.commit()
    await db.refresh(policy)

    await audit_log(
        db,
        event_type="global_routing_policy_activated",
        client_id="admin",
        details={
            "policy_id": str(policy.id),
            "version": policy.version,
            "previous_version_id": str(previous_version_id) if previous_version_id else None,
        },
    )

    return {
        "id": str(policy.id),
        "version": policy.version,
        "policy_json": policy_dict,
        "created_by": policy.created_by,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "status": policy.status,
        "previous_version_id": str(policy.previous_version_id)
        if policy.previous_version_id
        else None,
    }


@router.post("/policies/rollback")
async def rollback_policy(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(GlobalRoutingPolicyVersion).where(GlobalRoutingPolicyVersion.status == "active")
    res = await db.execute(stmt)
    current_active = res.scalars().first()
    if not current_active:
        raise HTTPException(status_code=400, detail="No active policy found to rollback")

    target_policy = None
    if current_active.previous_version_id:
        stmt_prev = select(GlobalRoutingPolicyVersion).where(
            GlobalRoutingPolicyVersion.id == current_active.previous_version_id
        )
        res_prev = await db.execute(stmt_prev)
        target_policy = res_prev.scalars().first()

    if not target_policy:
        stmt_fallback = select(GlobalRoutingPolicyVersion).where(
            GlobalRoutingPolicyVersion.version == current_active.version - 1
        )
        res_fallback = await db.execute(stmt_fallback)
        target_policy = res_fallback.scalars().first()

    if not target_policy:
        raise HTTPException(
            status_code=400, detail="No previous policy version found to rollback to"
        )

    current_active.status = "rolled_back"
    target_policy.status = "active"

    db.add(current_active)
    db.add(target_policy)
    await db.commit()

    await db.refresh(current_active)
    await db.refresh(target_policy)

    try:
        policy_dict = json.loads(target_policy.policy_json)
    except Exception:
        policy_dict = {}

    await audit_log(
        db,
        event_type="global_routing_policy_rolled_back",
        client_id="admin",
        details={
            "rolled_back_from_id": str(current_active.id),
            "rolled_back_to_id": str(target_policy.id),
            "version": target_policy.version,
        },
    )

    return {
        "id": str(target_policy.id),
        "version": target_policy.version,
        "policy_json": policy_dict,
        "created_by": target_policy.created_by,
        "created_at": target_policy.created_at.isoformat() if target_policy.created_at else None,
        "status": target_policy.status,
        "previous_version_id": str(target_policy.previous_version_id)
        if target_policy.previous_version_id
        else None,
    }


@router.get("/policies")
async def list_policies(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    stmt = select(GlobalRoutingPolicyVersion).order_by(GlobalRoutingPolicyVersion.version.desc())
    res = await db.execute(stmt)
    policies = res.scalars().all()

    out = []
    for p in policies:
        try:
            policy_dict = json.loads(p.policy_json)
        except Exception:
            policy_dict = {}
        out.append(
            {
                "id": str(p.id),
                "version": p.version,
                "policy_json": policy_dict,
                "created_by": p.created_by,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "status": p.status,
                "previous_version_id": str(p.previous_version_id)
                if p.previous_version_id
                else None,
            }
        )
    return out
