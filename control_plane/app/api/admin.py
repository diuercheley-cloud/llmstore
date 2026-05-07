import json
import os
import subprocess
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_circuit_breaker, get_inference_proxy
from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.core.time import utc_now
from app.db.session import get_db_session, get_redis
from app.models.api_key import ApiKey
from app.models.billing_invoice import BillingInvoice
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.models.customer_payment import CustomerPayment
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.models.pricing_rule import PricingRule
from app.models.quota_counter import QuotaCounter
from app.models.request_log import RequestLog
from app.models.usage_record import UsageRecord
from app.schemas.admin import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRotateResponse,
    BackendRouteInput,
    BackendRoutePatch,
    BillingPlanCreate,
    BillingPlanPatch,
    BillingPlanModelsPatch,
    BillingPlanRead,
    ClientBillingPlanPatch,
    ClientCreate,
    ClientPatch,
    ClientRead,
    InferenceBackendCreate,
    InferenceBackendPatch,
    InvoiceGenerateRequest,
    InvoiceMarkPaidRequest,
    ModelRegistryCreate,
    ModelDeleteRequest,
    ModelRegistryPatch,
    ModelPromptTestRequest,
    ModelReloadResponse,
    PaymentCreate,
    PaymentRead,
    PricingRuleRead,
    RoutingExplainRequest,
    RoutingExplainResponse,
    TestCommand,
    TestRunRequest,
    TestRunResponse,
)

WHITELISTED_COMMANDS = {
    "health-full": {"name": "Health full", "description": "Run full system health validation", "command": "./scripts/validate-system-health.sh --full"},
    "local-smoke": {"name": "Local production smoke", "description": "Run local production smoke tests", "command": "./scripts/local-production-smoke.sh"},
    "ui-health": {"name": "UI health", "description": "Check UI health", "command": "./scripts/ui-health.sh"},
    "validate-e2e": {"name": "Validate E2E", "description": "Run full E2E validation", "command": "./scripts/validate-e2e.sh"},
    "backup": {"name": "Backup", "description": "Trigger system backup", "command": "./scripts/backup.sh"},
    "dr-test": {"name": "DR test", "description": "Run Disaster Recovery test", "command": "./scripts/dr-test.sh"},
    "benchmark": {"name": "Benchmark quick", "description": "Run quick benchmark", "command": "./scripts/benchmark.sh --quick"},
    "test-fallback": {"name": "Real fallback test", "description": "Test real-world fallback routing", "command": "./scripts/test-real-fallback.sh"},
}
from app.services.billing import (
    build_invoice_preview,
    ensure_default_billing_plans,
    generate_monthly_invoices,
    get_current_usage_snapshot,
    list_client_billing_snapshots,
    refresh_billing_statuses,
    resolve_effective_plan,
    serialize_invoice,
)
from app.services.admin_model_management import (
    archive_model_identity,
    architecture_for_model,
    backend_container_snapshot,
    backend_runtime_capabilities,
    backend_service_name,
    detect_quantization,
    display_name_for_model,
    ensure_model_file_exists,
    list_model_files,
    merge_metadata,
    parse_metadata,
    prompt_template_for_payload,
    reasoning_defaults_for_model,
    remove_model_routes,
    resolve_models_dir,
    run_backend_docker_command,
    sanitize_model_filename,
    sync_allowed_plans,
)
from app.services.backend_registry import ensure_default_backends
from app.services.auth import require_admin
from app.services.export_reporting import (
    build_monthly_report,
    build_usage_by_client,
    build_usage_by_model,
    build_usage_summary,
    export_clients,
    export_invoices,
    export_payments,
    export_request_logs,
    export_security_events,
    export_usage,
    render_export_response,
)
from app.services.generation_jobs import get_admin_job_snapshot
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import (
    MODEL_REGISTRY_ROUTING_LOADS,
    apply_routing_policy,
    ensure_model_routing_loaded,
    get_model_by_id,
    get_routing_candidates,
    plan_routing_order,
    resolve_requested_model,
    serialize_routing_table,
)
from app.services.model_registry import ensure_default_model
from app.services.response_cache import clear_response_cache, get_response_cache_stats
from app.services.security_monitor import (
    log_security_event,
    list_security_events,
    observe_billing_status_metrics,
    suspend_client_for_security,
    unsuspend_client_for_security,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _load_backend_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_test_backend(backend: InferenceBackend) -> bool:
    metadata = _load_backend_metadata(backend.metadata_json)
    return bool(metadata.get("test_backend")) or backend.name.startswith("fallback-")


def _serialize_backend_admin(backend: InferenceBackend, health: dict | None = None) -> dict:
    runtime = backend_container_snapshot(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
        "service_name": backend_service_name(backend),
        "docker": runtime,
        "health": health,
        "created_at": backend.created_at.isoformat(),
        "updated_at": backend.updated_at.isoformat(),
    }


def _serialize_model_admin(model: ModelRegistry, health_map: dict[str, dict] | None = None) -> dict:
    ensure_model_routing_loaded(model)
    metadata = parse_metadata(model.metadata_json)
    architecture = architecture_for_model(model)
    reasoning = reasoning_defaults_for_model(model)
    backend_health = health_map.get(str(model.inference_backend_id)) if health_map and model.inference_backend_id else None
    return {
        "id": str(model.id),
        "display_name": display_name_for_model(model),
        "model_id": model.model_id,
        "model_alias": model.model_alias,
        "inference_backend_id": str(model.inference_backend_id) if model.inference_backend_id else None,
        "backend_name": model.inference_backend.name if model.inference_backend else None,
        "backend_url": model.inference_backend.backend_url if model.inference_backend else None,
        "provider": model.provider,
        "model_file": model.model_file,
        "status": model.status,
        "is_active": model.is_active,
        "is_default": model.is_default,
        "context_length": model.context_length,
        "prompt_template": model.prompt_template,
        "architecture": architecture,
        "quantization": detect_quantization(model.model_file),
        "allow_reasoning": reasoning["allow_reasoning"],
        "include_reasoning_default": reasoning["include_reasoning_default"],
        "metadata_json": model.metadata_json,
        "metadata": metadata,
        "routes": serialize_routing_table(model),
        "backend_health": backend_health,
        "created_at": model.created_at.isoformat(),
        "updated_at": model.updated_at.isoformat(),
    }


def _serialize_api_key_created(api_key: ApiKey, plaintext: str) -> ApiKeyCreated:
    return ApiKeyCreated(
        id=api_key.id,
        client_id=api_key.client_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=plaintext,
        scopes=json.loads(api_key.scopes_json) if api_key.scopes_json else None,
        expires_at=api_key.expires_at,
        allowed_ips=json.loads(api_key.allowed_ips_json) if api_key.allowed_ips_json else None,
        created_at=api_key.created_at,
    )


def _serialize_billing_plan_payload(payload: BillingPlanCreate) -> dict:
    plan_data = payload.model_dump()
    allowed_models = plan_data.pop("allowed_models", None)
    plan_data["allowed_models_json"] = json.dumps(allowed_models) if allowed_models is not None else None
    routing_policy = plan_data.pop("routing_policy", None)
    plan_data["routing_policy_json"] = json.dumps(routing_policy) if routing_policy is not None else None
    return plan_data


def _export_params(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    client_id: uuid.UUID | None = Query(default=None),
    format: str = Query(default="json", pattern="^(csv|json)$"),
):
    return {"start_date": start_date, "end_date": end_date, "client_id": client_id, "format": format}


async def _sync_model_backend_routes(session: AsyncSession, model: ModelRegistry, routes_payload: list[dict]) -> None:
    existing = {
        item.inference_backend_id: item
        for item in (
            await session.execute(
                select(ModelBackendRoute).where(ModelBackendRoute.model_registry_id == model.id)
            )
        ).scalars().all()
    }
    keep_backend_ids = set()
    for route_data in routes_payload:
        backend_id = route_data["inference_backend_id"]
        if await session.get(InferenceBackend, backend_id) is None:
            raise HTTPException(status_code=404, detail="backend not found")
        keep_backend_ids.add(backend_id)
        route = existing.get(backend_id)
        if route is None:
            route = ModelBackendRoute(model_registry_id=model.id, **route_data)
            session.add(route)
            continue
        route.priority = route_data["priority"]
        route.weight = route_data["weight"]
        route.state = route_data["state"]
        route.updated_at = utc_now()
    for backend_id, route in existing.items():
        if backend_id not in keep_backend_ids:
            await session.delete(route)


@router.post("/clients", response_model=ClientRead, status_code=201)
async def create_client(payload: ClientCreate, session: AsyncSession = Depends(get_db_session)):
    plans = await ensure_default_billing_plans(session)
    client_data = payload.model_dump()
    billing_plan_id = client_data.get("billing_plan_id") or plans["free"].id
    if await session.get(BillingPlan, billing_plan_id) is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    client_data["billing_plan_id"] = billing_plan_id
    for field in ["allowed_models", "ip_allowlist", "ip_blocklist"]:
        if field in client_data:
            val = client_data.pop(field)
            client_data[f"{field}_json"] = json.dumps(val) if val is not None else None
    client = Client(**client_data)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


@router.get("/clients", response_model=list[ClientRead])
async def list_clients(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(Client).where(Client.deleted_at.is_(None)).order_by(Client.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=404, detail="client not found")
    
    # não deletar se houver invoices pagas
    paid_invoices = await session.execute(
        select(BillingInvoice).where(BillingInvoice.client_id == client_id, BillingInvoice.status == "paid")
    )
    if paid_invoices.first() is not None:
        raise HTTPException(status_code=409, detail="cannot delete client with paid invoices")
    
    client.deleted_at = utc_now()
    # Revogar chaves
    keys = await session.execute(select(ApiKey).where(ApiKey.client_id == client_id))
    for key in keys.scalars().all():
        key.revoked_at = utc_now()
    
    await session.commit()


@router.patch("/clients/{client_id}", response_model=ClientRead)
async def patch_client(client_id: uuid.UUID, payload: ClientPatch, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "billing_plan_id" in patch_data and patch_data["billing_plan_id"] is not None:
        if await session.get(BillingPlan, patch_data["billing_plan_id"]) is None:
            raise HTTPException(status_code=404, detail="billing plan not found")
    if "allowed_models" in patch_data:
        patch_data["allowed_models_json"] = json.dumps(patch_data.pop("allowed_models")) if patch_data["allowed_models"] is not None else None
    if "ip_allowlist" in patch_data:
        patch_data["ip_allowlist_json"] = json.dumps(patch_data.pop("ip_allowlist")) if patch_data["ip_allowlist"] is not None else None
    if "ip_blocklist" in patch_data:
        patch_data["ip_blocklist_json"] = json.dumps(patch_data.pop("ip_blocklist")) if patch_data["ip_blocklist"] is not None else None
    for key, value in patch_data.items():
        setattr(client, key, value)
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.get("/billing/plans", response_model=list[BillingPlanRead])
async def list_billing_plans(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))
    return result.scalars().all()


@router.post("/billing/plans", response_model=BillingPlanRead, status_code=201)
async def create_billing_plan(payload: BillingPlanCreate, session: AsyncSession = Depends(get_db_session)):
    existing = await session.execute(select(BillingPlan).where(BillingPlan.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="billing plan code already exists")
    plan_data = _serialize_billing_plan_payload(payload)
    plan = BillingPlan(**plan_data)
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


@router.patch("/billing/plans/{plan_id}", response_model=BillingPlanRead)
async def patch_billing_plan(
    plan_id: uuid.UUID,
    payload: BillingPlanPatch,
    session: AsyncSession = Depends(get_db_session),
):
    plan = await session.get(BillingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "allowed_models" in patch_data:
        allowed_models = patch_data.pop("allowed_models")
        patch_data["allowed_models_json"] = json.dumps(allowed_models) if allowed_models is not None else None
    if "routing_policy" in patch_data:
        routing_policy = patch_data.pop("routing_policy")
        patch_data["routing_policy_json"] = json.dumps(routing_policy) if routing_policy is not None else None
    for key, value in patch_data.items():
        setattr(plan, key, value)
    plan.updated_at = utc_now()
    await session.commit()
    await session.refresh(plan)
    return plan


@router.get("/billing/pricing-rules", response_model=list[PricingRuleRead])
async def list_pricing_rules(session: AsyncSession = Depends(get_db_session)):
    rows = (await session.execute(select(PricingRule).order_by(PricingRule.created_at.asc()))).scalars().all()
    return [
        PricingRuleRead(
            id=row.id,
            billing_plan_id=row.billing_plan_id,
            currency=row.currency,
            monthly_price=float(row.monthly_price),
            overage_price_per_1k_tokens=float(row.overage_price_per_1k_tokens),
            description=row.description,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.patch("/clients/{client_id}/billing-plan", response_model=ClientRead)
async def set_client_billing_plan(
    client_id: uuid.UUID,
    payload: ClientBillingPlanPatch,
    session: AsyncSession = Depends(get_db_session),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    plan = await session.get(BillingPlan, payload.billing_plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    client.billing_plan_id = plan.id
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.patch("/billing/plans/{plan_id}/models", response_model=BillingPlanRead)
async def set_billing_plan_models(
    plan_id: uuid.UUID,
    payload: BillingPlanModelsPatch,
    session: AsyncSession = Depends(get_db_session),
):
    plan = await session.get(BillingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    plan.allowed_models_json = json.dumps(payload.allowed_models)
    plan.updated_at = utc_now()
    await session.commit()
    await session.refresh(plan)
    return plan


@router.post("/clients/{client_id}/block", response_model=ClientRead)
async def block_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = True
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/security/clients/{client_id}/suspend", response_model=ClientRead)
async def suspend_client_security(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await suspend_client_for_security(session, client, reason="manual_admin_security_action")
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/security/clients/{client_id}/unsuspend", response_model=ClientRead)
async def unsuspend_client_security(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await unsuspend_client_for_security(session, client)
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/clients/{client_id}/unblock", response_model=ClientRead)
async def unblock_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = False
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(payload: ApiKeyCreate, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    plaintext = generate_api_key()
    api_key = ApiKey(
        client_id=payload.client_id,
        name=payload.name,
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(payload.scopes) if payload.scopes else None,
        expires_at=payload.expires_at,
        allowed_ips_json=json.dumps(payload.allowed_ips) if payload.allowed_ips else None,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return _serialize_api_key_created(api_key, plaintext)


@router.post("/api-keys/{api_key_id}/rotate", response_model=ApiKeyRotateResponse)
async def rotate_api_key(api_key_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    current_key = await session.get(ApiKey, api_key_id)
    if current_key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    if current_key.revoked_at is not None:
        raise HTTPException(status_code=409, detail="api key already revoked")
    plaintext = generate_api_key()
    rotated_key = ApiKey(
        client_id=current_key.client_id,
        name=f"{current_key.name}-rotated",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        expires_at=current_key.expires_at,
        allowed_ips_json=current_key.allowed_ips_json,
        scopes_json=current_key.scopes_json,
    )
    current_key.revoked_at = utc_now()
    current_key.is_active = False
    session.add(rotated_key)
    await session.commit()
    await session.refresh(rotated_key)
    return ApiKeyRotateResponse(
        rotated_from_id=current_key.id,
        revoked_at=current_key.revoked_at,
        api_key=_serialize_api_key_created(rotated_key, plaintext),
    )


@router.get("/api-keys")
async def list_api_keys(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(
            ApiKey, 
            Client.name.label("client_name"),
            Client.created_at.label("client_created_at"),
            BillingPlan.name.label("plan_name")
        )
        .join(Client, Client.id == ApiKey.client_id)
        .outerjoin(BillingPlan, BillingPlan.id == Client.billing_plan_id)
        .order_by(desc(ApiKey.created_at))
        .limit(200)
    )
    rows = result.all()
    return [
        {
            "id": str(api_key.id),
            "client_id": str(api_key.client_id),
            "client_name": client_name,
            "client_created_at": client_created_at.isoformat(),
            "plan_name": plan_name or "N/A",
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at.isoformat(),
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "allowed_ips": json.loads(api_key.allowed_ips_json) if api_key.allowed_ips_json else None,
            "scopes": json.loads(api_key.scopes_json) if api_key.scopes_json else None,
        }
        for api_key, client_name, client_created_at, plan_name in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
async def revoke_api_key(api_key_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    api_key = await session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    api_key.revoked_at = utc_now()
    api_key.is_active = False
    await session.commit()


@router.get("/usage")
async def get_usage(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(QuotaCounter).order_by(desc(QuotaCounter.updated_at)).limit(200))
    rows = result.scalars().all()
    return [
        {
            "client_id": str(row.client_id),
            "period_start": row.period_start.isoformat(),
            "period_type": row.period_type,
            "used_tokens": row.used_tokens,
            "used_requests": row.used_requests,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/usage/summary")
async def get_usage_summary(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await observe_billing_status_metrics(session)
    queue_snapshot = proxy.queue_manager.get_snapshot()
    summary = await build_usage_summary(session, queue_snapshot=queue_snapshot)
    clients = await build_usage_by_client(session)
    models = await build_usage_by_model(session)

    # Enrich clients with invoice previews
    snapshots = await list_client_billing_snapshots(session)
    snapshots_by_client = {str(s["client"].id): s for s in snapshots}
    
    for client in clients:
        snapshot = snapshots_by_client.get(client["client_id"])
        if snapshot:
            client["invoice_preview"] = snapshot["invoice_preview"]
        else:
            client["invoice_preview"] = {
                "total_estimated": 0.0,
                "currency": "USD",
                "items": [],
            }

    plan_buckets: dict[str, dict] = {}
    total_estimated_cost = 0.0
    for client in clients:
        plan_code = client.get("billing_plan_code") or "unknown"
        bucket = plan_buckets.setdefault(
            plan_code,
            {
                "billing_plan_code": plan_code,
                "clients_total": 0,
                "requests_today": 0,
                "requests_month": 0,
                "tokens_today": 0,
                "tokens_month": 0,
                "errors_month": 0,
                "cache_hits_month": 0,
                "cache_misses_month": 0,
                "avg_latency_ms_month_weighted": 0.0,
                "estimated_cost_usd": 0.0,
            },
        )
        bucket["clients_total"] += 1
        bucket["requests_today"] += int(client["requests_today"])
        bucket["requests_month"] += int(client["requests_month"])
        bucket["tokens_today"] += int(client["tokens_today"])
        bucket["tokens_month"] += int(client["tokens_month"])
        bucket["errors_month"] += int(client["errors_month"])
        bucket["cache_hits_month"] += int(client["cache_hits_month"])
        bucket["cache_misses_month"] += int(client["cache_misses_month"])
        
        client_cost = float(client["invoice_preview"]["total_estimated"])
        bucket["estimated_cost_usd"] += client_cost
        total_estimated_cost += client_cost

        if int(client["requests_month"]) > 0:
            bucket["avg_latency_ms_month_weighted"] += float(client["avg_latency_ms_month"]) * int(client["requests_month"])

    plans = []
    for bucket in plan_buckets.values():
        requests_month = bucket["requests_month"]
        plans.append(
            {
                "billing_plan_code": bucket["billing_plan_code"],
                "clients_total": bucket["clients_total"],
                "requests_today": bucket["requests_today"],
                "requests_month": bucket["requests_month"],
                "tokens_today": bucket["tokens_today"],
                "tokens_month": bucket["tokens_month"],
                "errors_month": bucket["errors_month"],
                "cache_hits_month": bucket["cache_hits_month"],
                "cache_misses_month": bucket["cache_misses_month"],
                "cache_hit_rate_month": round(bucket["cache_hits_month"] / (bucket["cache_hits_month"] + bucket["cache_misses_month"]), 4)
                if (bucket["cache_hits_month"] + bucket["cache_misses_month"])
                else 0.0,
                "avg_latency_ms_month": round(bucket["avg_latency_ms_month_weighted"] / requests_month, 2) if requests_month else 0.0,
                "estimated_cost_usd": round(bucket["estimated_cost_usd"], 6),
            }
        )
    plans.sort(key=lambda item: item["requests_month"], reverse=True)
    return {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "totals": {
            "clients_total": summary["clients_total"],
            "requests_total": summary["requests_month"],
            "tokens_estimated_total": summary["tokens_month"],
            "errors_total": sum(item["errors_month"] for item in clients),
            "avg_latency_ms": summary["avg_latency_ms_month"],
            "estimated_cost_usd": round(total_estimated_cost, 6),
        },
        "plans": plans,
        "clients": clients,
        "models": models,
        "queues": queue_snapshot,
        "invoices": {
            "pending": summary["invoices_pending"],
            "paid": summary["invoices_paid"],
            "overdue": summary["invoices_overdue"],
            "total": summary["invoices_total"],
        },
        "client_status": {
            "active": summary["clients_active"],
            "suspended": summary["clients_suspended"],
            "blocked": summary["clients_blocked"],
        },
        "cache": {
            "hits_month": summary["cache_hits_month"],
            "misses_month": summary["cache_misses_month"],
            "hit_rate_month": summary["cache_hit_rate_month"],
        },
    }


@router.get("/usage/by-client")
async def get_usage_by_client(session: AsyncSession = Depends(get_db_session)):
    return await build_usage_by_client(session)


@router.get("/usage/by-model")
async def get_usage_by_model(session: AsyncSession = Depends(get_db_session)):
    return await build_usage_by_model(session)


@router.get("/revenue/summary")
async def get_revenue_summary(session: AsyncSession = Depends(get_db_session)):
    invoices = (await session.execute(select(BillingInvoice))).scalars().all()
    total_paid = sum(inv.total_amount for inv in invoices if inv.status == "paid")
    total_pending = sum(inv.total_amount for inv in invoices if inv.status == "pending")
    total_overdue = sum(inv.total_amount for inv in invoices if inv.status == "overdue")
    
    return {
        "generated_at": utc_now().isoformat(),
        "revenue_usd": float(total_paid),
        "pending_usd": float(total_pending),
        "overdue_usd": float(total_overdue),
        "invoices_paid": len([inv for inv in invoices if inv.status == "paid"]),
        "invoices_pending": len([inv for inv in invoices if inv.status == "pending"]),
        "invoices_overdue": len([inv for inv in invoices if inv.status == "overdue"]),
    }


@router.get("/rag/usage")
async def get_admin_rag_usage(session: AsyncSession = Depends(get_db_session)):
    from app.models.rag_document import RAGDocument
    from app.models.rag_usage_event import RagUsageEvent
    from app.services.quota import month_start
    from datetime import date
    
    # Usage by client
    stmt = (
        select(
            Client.id,
            Client.name,
            func.count(RAGDocument.id).label("doc_count"),
            func.coalesce(func.sum(RAGDocument.file_size_bytes), 0).label("storage_bytes")
        )
        .outerjoin(RAGDocument, RAGDocument.client_id == Client.id)
        .group_by(Client.id, Client.name)
    )
    results = (await session.execute(stmt)).all()
    
    from datetime import timezone, datetime
    start_of_month = datetime.combine(month_start(date.today()), datetime.min.time(), tzinfo=timezone.utc)
    
    usage_stmt = (
        select(
            RagUsageEvent.client_id,
            RagUsageEvent.event_type,
            func.sum(RagUsageEvent.quantity).label("total_quantity")
        )
        .where(RagUsageEvent.created_at >= start_of_month)
        .group_by(RagUsageEvent.client_id, RagUsageEvent.event_type)
    )
    usage_results = (await session.execute(usage_stmt)).all()
    
    client_usage = {}
    for row in usage_results:
        cid = str(row.client_id)
        if cid not in client_usage:
            client_usage[cid] = {"queries": 0, "pages": 0}
        if row.event_type == "rag_query":
            client_usage[cid]["queries"] = row.total_quantity
        elif row.event_type == "pages_processed":
            client_usage[cid]["pages"] = row.total_quantity
            
    return [
        {
            "client_id": str(r.id),
            "client_name": r.name,
            "documents_count": r.doc_count,
            "storage_mb": round(r.storage_bytes / (1024 * 1024), 2),
            "queries_month": client_usage.get(str(r.id), {}).get("queries", 0),
            "pages_month": client_usage.get(str(r.id), {}).get("pages", 0)
        }
        for r in results
    ]


@router.get("/billing/invoices/preview")
async def preview_invoices(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session, proxy)
    return {
        "generated_at": summary["generated_at"],
        "totals": {
            "clients_total": summary["totals"]["clients_total"],
            "estimated_cost_usd": summary["totals"]["estimated_cost_usd"],
        },
        "clients": [
            {
                "client_id": item["client_id"],
                "name": item["name"],
                "billing_plan_code": item["billing_plan_code"],
                "invoice_preview": item["invoice_preview"],
            }
            for item in summary["clients"]
        ],
    }


@router.get("/billing/clients/{client_id}/invoice/preview")
async def preview_client_invoice(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session, proxy)
    client_entry = next((item for item in summary["clients"] if item["client_id"] == str(client_id)), None)
    if client_entry is None:
        raise HTTPException(status_code=404, detail="client not found")
    return {
        "client_id": client_entry["client_id"],
        "name": client_entry["name"],
        "billing_plan_code": client_entry["billing_plan_code"],
        "invoice_preview": client_entry["invoice_preview"],
    }


@router.post("/billing/invoices/generate", status_code=201)
async def generate_invoices(payload: InvoiceGenerateRequest, session: AsyncSession = Depends(get_db_session)):
    if payload.client_id is not None and await session.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=404, detail="client not found")
    result = await generate_monthly_invoices(
        session,
        reference_datetime=utc_now(),
        invoice_day=settings.billing_invoice_day,
        due_in_days=payload.due_in_days,
        suspend_after_days=settings.billing_suspend_after_days,
        payment_method=payload.payment_method,
        payment_instructions=payload.payment_instructions,
        force=True,
        client_id=payload.client_id,
    )
    await session.commit()
    created = result["created"]
    updated = result["updated"]
    invoice_ids = [item.id for item in [*created, *updated]]
    invoices_by_id = {}
    if invoice_ids:
        refreshed = (
            await session.execute(
                select(BillingInvoice)
                .options(selectinload(BillingInvoice.payments))
                .where(BillingInvoice.id.in_(invoice_ids))
            )
        ).scalars().all()
        invoices_by_id = {item.id: item for item in refreshed}
    return {
        "generated_at": result["generated_at"],
        "created": [serialize_invoice(invoices_by_id.get(item.id, item)) for item in created],
        "updated": [serialize_invoice(invoices_by_id.get(item.id, item)) for item in updated],
        "skipped": result["skipped"],
        "reason": result["reason"],
    }


@router.post("/billing/run-cycle")
async def run_billing_cycle(session: AsyncSession = Depends(get_db_session)):
    result = await generate_monthly_invoices(
        session,
        reference_datetime=utc_now(),
        invoice_day=settings.billing_invoice_day,
        due_in_days=settings.billing_due_days,
        suspend_after_days=settings.billing_suspend_after_days,
        payment_method="manual_pix",
        payment_instructions="billing-cycle",
        force=False,
    )
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    return {
        "generated_at": result["generated_at"],
        "created_count": len(result["created"]),
        "updated_count": len(result["updated"]),
        "skipped_count": len(result["skipped"]),
        "reason": result["reason"],
    }


@router.get("/billing/invoices")
async def list_invoices(session: AsyncSession = Depends(get_db_session)):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    invoices = (
        await session.execute(
            select(BillingInvoice)
            .options(
                selectinload(BillingInvoice.client),
                selectinload(BillingInvoice.billing_plan),
                selectinload(BillingInvoice.payments),
            )
            .order_by(desc(BillingInvoice.created_at))
            .limit(200)
        )
    ).scalars().all()
    payments = (
        await session.execute(
            select(CustomerPayment)
            .order_by(desc(CustomerPayment.created_at))
            .limit(200)
        )
    ).scalars().all()
    return {
        "generated_at": utc_now().isoformat(),
        "summary": {
            "overdue_invoices": sum(1 for invoice in invoices if invoice.status == "overdue"),
            "past_due_clients": len({str(invoice.client_id) for invoice in invoices if invoice.client and invoice.client.billing_status == "past_due"}),
            "suspended_clients": len({str(invoice.client_id) for invoice in invoices if invoice.client and invoice.client.billing_status == "suspended"}),
        },
        "invoices": [
            {
                **serialize_invoice(invoice),
                "client_name": invoice.client.name if invoice.client else None,
                "client_billing_status": invoice.client.billing_status if invoice.client else None,
                "billing_plan_code": invoice.billing_plan.code if invoice.billing_plan else None,
            }
            for invoice in invoices
        ],
        "payments": [
            {
                "id": str(payment.id),
                "invoice_id": str(payment.invoice_id),
                "client_id": str(payment.client_id),
                "status": payment.status,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference,
                "note": payment.note,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "cancelled_at": payment.cancelled_at.isoformat() if payment.cancelled_at else None,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat(),
            }
            for payment in payments
        ],
    }


@router.patch("/billing/invoices/{invoice_id}/mark-overdue")
async def mark_invoice_overdue(
    invoice_id: uuid.UUID,
    simulate_suspension: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session)
):
    from datetime import timedelta
    invoice = await session.get(BillingInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="paid invoice cannot be marked overdue")
    invoice.status = "overdue"
    if simulate_suspension:
        invoice.due_at = utc_now() - timedelta(days=settings.billing_suspend_after_days + 1)
    invoice.updated_at = utc_now()
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    return {"status": "overdue", "invoice_id": str(invoice.id)}


@router.get("/billing/payments", response_model=list[PaymentRead])
async def list_payments(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(CustomerPayment).order_by(desc(CustomerPayment.created_at)).limit(500))
    return result.scalars().all()


@router.post("/billing/payments", response_model=PaymentRead, status_code=201)
async def create_payment(payload: PaymentCreate, session: AsyncSession = Depends(get_db_session)):
    invoice = await session.get(BillingInvoice, payload.invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    payment = CustomerPayment(
        invoice_id=payload.invoice_id,
        client_id=invoice.client_id,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        note=payload.note,
        status="paid" if payload.paid_at else "pending",
        paid_at=payload.paid_at,
    )
    session.add(payment)
    if payload.paid_at and invoice.status != "paid":
        # If paying full amount or more, mark invoice as paid
        # Simple logic: if any payment is 'paid', we consider it progress. 
        # For simplicity, if this payment is marked 'paid', we mark invoice paid.
        invoice.status = "paid"
        invoice.paid_at = payload.paid_at
        if invoice.client:
            invoice.client.billing_status = "active"
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(payment)
    return payment


@router.patch("/billing/payments/{payment_id}/cancel")
async def cancel_payment(payment_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    payment = await session.get(CustomerPayment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    if payment.status == "cancelled":
        raise HTTPException(status_code=409, detail="payment already cancelled")
    payment.status = "cancelled"
    payment.cancelled_at = utc_now()
    payment.updated_at = utc_now()
    await session.commit()
    return {"status": "cancelled", "payment_id": str(payment.id)}


@router.patch("/billing/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    payload: InvoiceMarkPaidRequest,
    session: AsyncSession = Depends(get_db_session),
):
    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.client), selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="cancelled invoice cannot be paid")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="invoice already paid")

    paid_at = payload.paid_at or utc_now()
    invoice.status = "paid"
    invoice.paid_at = paid_at
    invoice.cancelled_at = None
    invoice.updated_at = utc_now()

    payment = next((item for item in invoice.payments if item.status in {"pending", "overdue"}), None)
    if payment is None:
        payment = CustomerPayment(
            invoice_id=invoice.id,
            client_id=invoice.client_id,
            amount=invoice.total_amount,
            currency=invoice.currency,
            payment_method=payload.payment_method,
            status="paid",
        )
        session.add(payment)
    payment.status = "paid"
    payment.amount = Decimal(str(payload.amount_paid)) if payload.amount_paid is not None else invoice.total_amount
    payment.currency = invoice.currency
    payment.payment_method = payload.payment_method
    payment.payment_reference = payload.payment_reference
    payment.note = payload.note
    payment.paid_at = paid_at
    payment.cancelled_at = None
    payment.updated_at = utc_now()

    if invoice.client is not None:
        invoice.client.billing_status = "active"
        invoice.client.updated_at = utc_now()

    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(invoice, attribute_names=["payments", "client"])
    return {
        "status": "paid",
        "invoice": {
            **serialize_invoice(invoice),
            "client_name": invoice.client.name if invoice.client else None,
            "client_billing_status": invoice.client.billing_status if invoice.client else None,
        },
    }


@router.patch("/billing/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.client), selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="paid invoice cannot be cancelled")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="invoice already cancelled")

    invoice.status = "cancelled"
    invoice.cancelled_at = utc_now()
    invoice.updated_at = utc_now()
    for payment in invoice.payments:
        if payment.status != "paid":
            payment.status = "cancelled"
            payment.cancelled_at = utc_now()
            payment.updated_at = utc_now()

    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(invoice, attribute_names=["payments", "client"])
    return {
        "status": "cancelled",
        "invoice": {
            **serialize_invoice(invoice),
            "client_name": invoice.client.name if invoice.client else None,
            "client_billing_status": invoice.client.billing_status if invoice.client else None,
        },
    }


@router.get("/requests")
async def get_requests(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(RequestLog).order_by(desc(RequestLog.created_at)).limit(200))
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "client_id": str(row.client_id),
            "model": row.model,
            "endpoint": row.endpoint,
            "prompt_tokens_estimated": row.prompt_tokens_estimated,
            "completion_tokens_estimated": row.completion_tokens_estimated,
            "latency_ms": row.latency_ms,
            "estimated_cost_usd": float(row.estimated_cost_usd or 0),
            "status": row.http_status,
            "backend_name": row.backend_name,
            "attempts": row.attempts,
            "fallback_used": row.fallback_used,
            "cache_hit": row.cache_hit,
            "backend_errors": json.loads(row.backend_errors_json) if row.backend_errors_json else [],
            "error": row.error_message,
            "correlation_id": row.correlation_id,
            "source_ip": row.source_ip,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


from app.schemas.quality import SystemPromptUpdate, PromptTemplateUpdate


@router.patch("/clients/{client_id}/system-prompt", response_model=ClientRead)
async def patch_client_system_prompt(
    client_id: uuid.UUID,
    payload: SystemPromptUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.system_prompt = payload.system_prompt
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.patch("/models/{model_id}/prompt-template")
async def patch_model_prompt_template(
    model_id: uuid.UUID,
    payload: PromptTemplateUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    model.prompt_template = payload.prompt_template
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {
        "id": str(model.id),
        "model_id": model.model_id,
        "prompt_template": model.prompt_template,
        "updated_at": model.updated_at.isoformat(),
    }


@router.get("/security/events")
async def get_security_events(session: AsyncSession = Depends(get_db_session)):
    return await list_security_events(session)


@router.get("/export/clients")
async def export_clients_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_clients(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("clients", rows, params["format"])


@router.get("/export/usage")
async def export_usage_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_usage(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("usage", rows, params["format"])


@router.get("/export/invoices")
async def export_invoices_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_invoices(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("invoices", rows, params["format"])


@router.get("/export/payments")
async def export_payments_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_payments(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("payments", rows, params["format"])


@router.get("/export/security-events")
async def export_security_events_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_security_events(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("security-events", rows, params["format"])


@router.get("/export/request-logs")
async def export_request_logs_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_request_logs(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("request-logs", rows, params["format"])


@router.get("/reports/monthly")
async def monthly_report(
    month: str | None = Query(default=None, description="YYYY-MM"),
    session: AsyncSession = Depends(get_db_session),
):
    return await build_monthly_report(session, month=month)


@router.get("/cache/stats")
async def cache_stats(session: AsyncSession = Depends(get_db_session)):
    return await get_response_cache_stats(session)


@router.delete("/cache/responses")
async def cache_clear(session: AsyncSession = Depends(get_db_session)):
    deleted = await clear_response_cache(session)
    await session.commit()
    return {"status": "cleared", "deleted_entries": deleted}


@router.get("/models")
async def get_models(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_backends(session)
    await session.flush()
    result = await session.execute(
        select(ModelRegistry)
        .options(*MODEL_REGISTRY_ROUTING_LOADS)
        .order_by(ModelRegistry.created_at.desc())
    )
    registry = result.scalars().all()
    backends = (
        await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))
    ).scalars().all()
    backend_health = [await proxy.health_backend(item) for item in backends]
    health_map = {item["backend_id"]: item for item in backend_health}
    plans = (await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))).scalars().all()
    return {
        "registry": [_serialize_model_admin(item, health_map) for item in registry if item.status != "soft-deleted"],
        "plan_access": [
            {
                "billing_plan_id": str(plan.id),
                "billing_plan_code": plan.code,
                "allowed_models_json": plan.allowed_models_json,
            }
            for plan in plans
        ],
        "backends": [_serialize_backend_admin(item, health_map.get(str(item.id))) for item in backends],
    }


@router.get("/backends")
async def list_backends(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_backends(session)
    await session.commit()
    rows = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    return [_serialize_backend_admin(item, await proxy.health_backend(item)) for item in rows]


@router.post("/backends", status_code=201)
async def create_backend(payload: InferenceBackendCreate, session: AsyncSession = Depends(get_db_session)):
    existing = await session.execute(select(InferenceBackend).where(InferenceBackend.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="backend name already exists")
    if payload.is_default:
        defaults = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_default.is_(True)))).scalars().all()
        for item in defaults:
            item.is_default = False
    backend = InferenceBackend(**payload.model_dump())
    session.add(backend)
    await session.commit()
    await session.refresh(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
    }


@router.post("/backends/test-connection")
async def test_backend_connection(
    payload: InferenceBackendCreate,
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    """
    Testa a conexão com um backend antes de cadastrá-lo.
    """
    base_url = payload.backend_url
    api_key = None
    if payload.metadata_json:
        try:
            metadata = json.loads(payload.metadata_json)
            api_key = metadata.get("api_key")
        except json.JSONDecodeError:
            pass
            
    ok = await proxy.health_url(base_url, payload.healthcheck_path)
    if not ok and payload.provider == "openai_compatible":
         # Try common fallbacks
         ok = await proxy.health_url(base_url, "/v1/models")
         if not ok:
             ok = await proxy.health_url(base_url, "/models")
             
    return {"ok": ok}


@router.post("/backends/list-models")
async def list_backend_models(
    payload: InferenceBackendCreate,
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    """
    Lista os modelos disponíveis em um backend antes de cadastrá-lo.
    """
    base_url = payload.backend_url
    api_key = None
    if payload.metadata_json:
        try:
            metadata = json.loads(payload.metadata_json)
            api_key = metadata.get("api_key")
        except json.JSONDecodeError:
            pass
            
    return await proxy.list_models(base_url=base_url, api_key=api_key)


@router.patch("/backends/{backend_id}")
async def patch_backend(
    backend_id: uuid.UUID,
    payload: InferenceBackendPatch,
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "name" in patch_data and patch_data["name"] != backend.name:
        existing = await session.execute(select(InferenceBackend).where(InferenceBackend.name == patch_data["name"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="backend name already exists")
    if patch_data.get("is_default") is True:
        defaults = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_default.is_(True), InferenceBackend.id != backend_id))).scalars().all()
        for item in defaults:
            item.is_default = False
    for key, value in patch_data.items():
        setattr(backend, key, value)
    backend.updated_at = utc_now()
    await session.commit()
    await session.refresh(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
    }


@router.get("/backends/{backend_id}/health")
async def backend_health(
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    return {
        "backend": _serialize_backend_admin(backend, await proxy.health_backend(backend)),
        "docker": backend_container_snapshot(backend),
    }


@router.get("/backends/{backend_id}/logs")
async def backend_logs(
    backend_id: uuid.UUID,
    tail: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    service_name = backend_service_name(backend)
    if not service_name:
        raise HTTPException(status_code=409, detail="backend is not mapped to a compose service")
    result = run_backend_docker_command(backend, "logs", "--tail", str(tail), service_name, timeout_seconds=30)
    if not result.ok:
        raise HTTPException(status_code=409, detail=result.detail or result.stderr or "backend logs unavailable")
    return {
        "backend_id": str(backend.id),
        "backend_name": backend.name,
        "service_name": service_name,
        "tail": tail,
        "logs": result.stdout[-20000:],
    }


async def _run_backend_action(
    backend_id: uuid.UUID,
    action: str,
    session: AsyncSession,
) -> dict:
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    capabilities = backend_runtime_capabilities(backend)
    if not capabilities["docker_actions_allowed"]:
        detail = "docker actions disabled"
        if settings.public_exposure:
            detail = "backend docker action blocked when PUBLIC_EXPOSURE=true"
        elif not settings.test_tools_enabled:
            detail = "backend docker action blocked when TEST_TOOLS_ENABLED=false"
        raise HTTPException(status_code=403, detail=detail)
    service_name = backend_service_name(backend)
    if not service_name:
        raise HTTPException(status_code=409, detail="backend is not mapped to a compose service")
    command_map = {
        "start": ("up", "-d", service_name),
        "stop": ("stop", service_name),
        "restart": ("restart", service_name),
    }
    result = run_backend_docker_command(backend, *command_map[action], timeout_seconds=120)
    if not result.ok:
        raise HTTPException(status_code=409, detail=result.detail or result.stderr or "docker action failed")
    backend.status = "starting" if action == "start" else "stopped" if action == "stop" else "restarting"
    backend.is_active = action != "stop"
    backend.updated_at = utc_now()
    await log_security_event(
        session,
        event_type=f"admin_backend_{action}",
        severity="high",
        title=f"Backend {action} triggered via Admin Lab",
        details={"backend_name": backend.name, "service_name": service_name},
    )
    await session.commit()
    return {
        "status": action,
        "backend_id": str(backend.id),
        "backend_name": backend.name,
        "service_name": service_name,
        "docker_stdout": result.stdout[-4000:],
        "docker_stderr": result.stderr[-2000:],
    }


@router.post("/backends/{backend_id}/start")
async def start_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "start", session)


@router.post("/backends/{backend_id}/stop")
async def stop_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "stop", session)


@router.post("/backends/{backend_id}/restart")
async def restart_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "restart", session)


@router.patch("/models/{model_id}/routes/{backend_id}")
async def patch_model_backend_route(
    model_id: uuid.UUID,
    backend_id: uuid.UUID,
    payload: BackendRoutePatch,
    session: AsyncSession = Depends(get_db_session),
):
    route = (
        await session.execute(
            select(ModelBackendRoute).where(
                ModelBackendRoute.model_registry_id == model_id,
                ModelBackendRoute.inference_backend_id == backend_id,
            )
        )
    ).scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="model backend route not found")
    patch_data = payload.model_dump(exclude_unset=True)
    for key, value in patch_data.items():
        setattr(route, key, value)
    route.updated_at = utc_now()
    await session.commit()
    await session.refresh(route)
    return {
        "id": str(route.id),
        "model_id": str(route.model_registry_id),
        "backend_id": str(route.inference_backend_id),
        "priority": route.priority,
        "weight": route.weight,
        "state": route.state,
        "updated_at": route.updated_at.isoformat(),
    }


@router.post("/backends/circuit-breaker/reset")
async def reset_backend_circuit_breaker():
    breaker = get_circuit_breaker()
    await breaker.reset()
    return {
        "status": "ok",
        "detail": "circuit breaker reset",
        "reset_at": utc_now().isoformat(),
        "scope": "in-memory control-plane process",
    }


@router.get("/jobs")
async def list_generation_jobs(
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
):
    return await get_admin_job_snapshot(session, redis)


@router.get("/backends/health")
async def backends_health(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    rows = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    return {
        "generated_at": utc_now().isoformat(),
        "backends": [await proxy.health_backend(item) for item in rows],
    }


@router.get("/backends/routing")
async def backends_routing(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    backend_rows = (
        await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))
    ).scalars().all()
    backend_health = {
        item["backend_id"]: item
        for item in [await proxy.health_backend(row) for row in backend_rows]
    }
    models = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .order_by(ModelRegistry.created_at.asc())
        )
    ).scalars().all()
    model_rows = []
    summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "disabled": 0}
    for item in models:
        routes = []
        for route in sorted(
            item.backend_routes,
            key=lambda entry: (entry.priority, -(entry.weight or 0), entry.created_at),
        ):
            backend = route.inference_backend
            if backend is None:
                continue
            summary[route.state] = summary.get(route.state, 0) + 1
            backend_snapshot = backend_health.get(str(backend.id), {})
            routes.append(
                {
                    "route_id": str(route.id) if route.id else None,
                    "backend_id": str(backend.id),
                    "backend_name": backend.name,
                    "backend_url": backend.backend_url,
                    "provider": backend.provider,
                    "priority": route.priority,
                    "weight": route.weight,
                    "state": route.state,
                    "health": backend_snapshot.get("ok"),
                    "latency_ms": backend_snapshot.get("latency_ms"),
                    "backend_is_active": backend.is_active,
                    "backend_status": backend.status,
                    "is_test_backend": _is_test_backend(backend),
                    "eligible_for_routing": bool(backend.is_active and route.state != "disabled"),
                }
            )
        model_rows.append(
            {
                "id": str(item.id),
                "model_id": item.model_id,
                "model_alias": item.model_alias,
                "is_default": item.is_default,
                "routing_policy": "weighted_priority_fallback",
                "routes": routes,
            }
        )
    return {
        "generated_at": utc_now().isoformat(),
        "summary": summary,
        "models": model_rows,
    }


@router.get("/models/files")
async def get_model_files(session: AsyncSession = Depends(get_db_session)):
    models_dir = resolve_models_dir()
    files = await list_model_files(session)
    warning = None
    if not models_dir.exists():
        warning = f"models directory not found: {models_dir}"
    elif not models_dir.is_dir():
        warning = f"models path is not a directory: {models_dir}"
    elif not files:
        warning = f"Nenhum arquivo .gguf encontrado em {models_dir}"
    return {
        "models_dir": str(models_dir),
        "models_dir_exists": models_dir.exists(),
        "models_dir_is_dir": models_dir.is_dir(),
        "files": files,
        "warning": warning,
    }


@router.post("/models", status_code=201)
async def create_model(payload: ModelRegistryCreate, session: AsyncSession = Depends(get_db_session)):
    backend_id = payload.inference_backend_id
    if backend_id is not None and payload.create_backend is not None:
        raise HTTPException(status_code=409, detail="choose an existing backend or create a new one")
    if payload.create_backend is not None:
        existing_backend = await session.execute(
            select(InferenceBackend).where(InferenceBackend.name == payload.create_backend.name)
        )
        if existing_backend.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="backend name already exists")
        backend_payload = payload.create_backend.model_dump()
        backend = InferenceBackend(**backend_payload)
        session.add(backend)
        await session.flush()
        backend_id = backend.id
    if backend_id is not None and await session.get(InferenceBackend, backend_id) is None:
        raise HTTPException(status_code=404, detail="backend not found")
    try:
        model_file = sanitize_model_filename(payload.model_file, provider=payload.provider)
        if payload.provider == "llama.cpp":
            ensure_model_file_exists(model_file, provider=payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clauses = [ModelRegistry.model_id == payload.model_id]
    if payload.model_alias:
        clauses.append(ModelRegistry.model_alias == payload.model_alias)
    existing = await session.execute(select(ModelRegistry).where(or_(*clauses)))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="model id or alias already exists")
    metadata_json = merge_metadata(
        payload.metadata_json,
        {
            "display_name": payload.display_name,
            "allow_reasoning": payload.allow_reasoning,
            "include_reasoning_default": payload.include_reasoning_default,
        },
    )
    prompt_template = prompt_template_for_payload(
        prompt_template=payload.prompt_template,
        model_id=payload.model_id,
        model_file=model_file,
        model_alias=payload.model_alias,
        metadata_json=metadata_json,
    )
    if payload.is_default:
        defaults = (await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True)))).scalars().all()
        for item in defaults:
            item.is_default = False
    model = ModelRegistry(
        model_id=payload.model_id,
        model_alias=payload.model_alias,
        inference_backend_id=backend_id,
        provider=payload.provider,
        model_file=model_file,
        context_length=payload.context_length,
        is_active=payload.is_active,
        is_default=payload.is_default,
        status=payload.status,
        prompt_template=prompt_template,
        metadata_json=metadata_json,
    )
    session.add(model)
    await session.flush()
    routes_payload = [item.model_dump() for item in payload.backend_routes]
    if not routes_payload and backend_id is not None:
        routes_payload = [{"inference_backend_id": backend_id, "priority": 1, "weight": 100, "state": "healthy"}]
    if routes_payload:
        await _sync_model_backend_routes(session, model, routes_payload)
    try:
        await sync_allowed_plans(session, model=model, allowed_plan_codes=payload.allowed_plan_codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_security_event(
        session,
        event_type="admin_model_created",
        severity="medium",
        title="Model created via Admin Lab",
        details={"model_id": model.model_id, "model_alias": model.model_alias, "provider": model.provider},
    )
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after create")
    return _serialize_model_admin(loaded_model)


@router.patch("/models/{model_id}")
async def patch_model(
    model_id: uuid.UUID,
    payload: ModelRegistryPatch,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    patch_data = payload.model_dump(exclude_unset=True)
    routes_payload = patch_data.pop("backend_routes", None)
    allowed_plan_codes = patch_data.pop("allowed_plan_codes", None)
    display_name = patch_data.pop("display_name", None) if "display_name" in patch_data else None
    allow_reasoning = patch_data.pop("allow_reasoning", None) if "allow_reasoning" in patch_data else None
    include_reasoning_default = patch_data.pop("include_reasoning_default", None) if "include_reasoning_default" in patch_data else None
    if "inference_backend_id" in patch_data and patch_data["inference_backend_id"] is not None:
        if await session.get(InferenceBackend, patch_data["inference_backend_id"]) is None:
            raise HTTPException(status_code=404, detail="backend not found")
    if "model_alias" in patch_data and patch_data["model_alias"] is not None:
        existing = await session.execute(
            select(ModelRegistry).where(ModelRegistry.model_alias == patch_data["model_alias"], ModelRegistry.id != model_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="model alias already exists")
    if patch_data.get("is_default") is True:
        defaults = (
            await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True), ModelRegistry.id != model_id))
        ).scalars().all()
        for item in defaults:
            item.is_default = False
    if patch_data.get("is_active") is False and model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be disabled")
    provider = patch_data.get("provider", model.provider)
    if "model_file" in patch_data:
        try:
            patch_data["model_file"] = sanitize_model_filename(patch_data["model_file"], provider=provider)
            if provider == "llama.cpp":
                ensure_model_file_exists(patch_data["model_file"], provider=provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    for key, value in patch_data.items():
        setattr(model, key, value)
    metadata_updates = {}
    if "display_name" in payload.model_fields_set:
        metadata_updates["display_name"] = display_name
    if "allow_reasoning" in payload.model_fields_set:
        metadata_updates["allow_reasoning"] = allow_reasoning
    if "include_reasoning_default" in payload.model_fields_set:
        metadata_updates["include_reasoning_default"] = include_reasoning_default
    if metadata_updates:
        model.metadata_json = merge_metadata(model.metadata_json, metadata_updates)
    if "prompt_template" in patch_data or "model_file" in patch_data or "provider" in patch_data or "model_alias" in patch_data:
        model.prompt_template = prompt_template_for_payload(
            prompt_template=model.prompt_template,
            model_id=model.model_id,
            model_file=model.model_file,
            model_alias=model.model_alias,
            metadata_json=model.metadata_json,
        )
    if routes_payload is not None:
        await _sync_model_backend_routes(session, model, routes_payload)
    elif patch_data.get("inference_backend_id") is not None:
        existing_route = next(
            (item for item in model.backend_routes if item.inference_backend_id == patch_data["inference_backend_id"]),
            None,
        )
        if existing_route is None:
            await _sync_model_backend_routes(
                session,
                model,
                [
                    *[{"inference_backend_id": route.inference_backend_id, "priority": route.priority, "weight": route.weight, "state": route.state} for route in model.backend_routes],
                    {"inference_backend_id": patch_data["inference_backend_id"], "priority": 1, "weight": 100, "state": "healthy"},
                ],
            )
    try:
        await sync_allowed_plans(session, model=model, allowed_plan_codes=allowed_plan_codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    model.updated_at = utc_now()
    await log_security_event(
        session,
        event_type="admin_model_updated",
        severity="medium",
        title="Model updated via Admin Lab",
        details={"model_id": model.model_id, "model_alias": model.model_alias},
    )
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after update")
    return _serialize_model_admin(loaded_model)


@router.post("/models/{model_id}/set-default")
async def set_default_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    defaults = (
        await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True), ModelRegistry.id != model_id))
    ).scalars().all()
    for item in defaults:
        item.is_default = False
    model.is_default = True
    model.is_active = True
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "default-updated", "id": str(model.id)}


@router.post("/models/{model_id}/routes")
async def create_model_route(
    model_id: uuid.UUID,
    payload: BackendRouteInput,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if await session.get(InferenceBackend, payload.inference_backend_id) is None:
        raise HTTPException(status_code=404, detail="backend not found")
    if any(route.inference_backend_id == payload.inference_backend_id for route in model.backend_routes):
        raise HTTPException(status_code=409, detail="route already exists for this backend")
    routes_payload = [
        {"inference_backend_id": route.inference_backend_id, "priority": route.priority, "weight": route.weight, "state": route.state}
        for route in model.backend_routes
    ]
    routes_payload.append(payload.model_dump())
    await _sync_model_backend_routes(session, model, routes_payload)
    if model.inference_backend_id is None:
        model.inference_backend_id = payload.inference_backend_id
    model.updated_at = utc_now()
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after route create")
    return _serialize_model_admin(loaded_model)


@router.delete("/models/{model_id}/routes/{backend_id}")
async def delete_model_route(
    model_id: uuid.UUID,
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    route = (
        await session.execute(
            select(ModelBackendRoute).where(
                ModelBackendRoute.model_registry_id == model_id,
                ModelBackendRoute.inference_backend_id == backend_id,
            )
        )
    ).scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="model backend route not found")
    await session.delete(route)
    model = await session.get(ModelRegistry, model_id)
    if model is not None and model.inference_backend_id == backend_id:
        model.inference_backend_id = None
        model.updated_at = utc_now()
    await session.commit()
    return {"status": "route-removed", "model_id": str(model_id), "backend_id": str(backend_id)}


@router.post("/models/{model_id}/enable")
async def enable_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = (
        await session.execute(
            select(ModelRegistry).options(selectinload(ModelRegistry.inference_backend)).where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    model.is_active = True
    model.status = "configured"
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "enabled", "id": str(model.id)}


@router.post("/models/{model_id}/disable")
async def disable_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be disabled")
    model.is_active = False
    model.status = "disabled"
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "disabled", "id": str(model.id)}


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: uuid.UUID,
    payload: ModelDeleteRequest,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(selectinload(ModelRegistry.backend_routes))
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be removed")
    route_count = len(model.backend_routes)
    if route_count and not payload.confirm_route_removal:
        raise HTTPException(status_code=409, detail="model still has active backend routes; confirm route removal")
    request_count = (
        await session.execute(
            select(func.count(RequestLog.id)).where(
                or_(
                    RequestLog.model == model.model_id,
                    RequestLog.model == (model.model_alias or ""),
                )
            )
        )
    ).scalar_one()
    if payload.mode in {"hard", "register-only"} and request_count:
        raise HTTPException(status_code=409, detail="model has request history; use soft delete or disable it")
    removed_routes = await remove_model_routes(session, model)
    result_status = "deleted"
    if payload.mode == "soft" or (payload.mode == "auto" and request_count):
        archive_model_identity(model)
        result_status = "soft-deleted"
    else:
        await session.delete(model)
    await log_security_event(
        session,
        event_type="admin_model_deleted",
        severity="high",
        title="Model removed via Admin Lab",
        details={
            "model_id": model.model_id,
            "model_alias": model.model_alias,
            "mode": payload.mode,
            "request_count": int(request_count or 0),
            "removed_routes": removed_routes,
            "result": result_status,
        },
    )
    await session.commit()
    return {
        "status": result_status,
        "id": str(model_id),
        "request_count": int(request_count or 0),
        "removed_routes": removed_routes,
    }


@router.post("/models/{model_id}/test-prompt")
async def test_model_prompt(
    model_id: uuid.UUID,
    payload: ModelPromptTestRequest,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(
                selectinload(ModelRegistry.inference_backend),
                selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
            )
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    include_reasoning = payload.include_reasoning
    if include_reasoning is None:
        include_reasoning = bool(reasoning_defaults_for_model(model)["include_reasoning_default"])
    body = {
        "model": model.model_id,
        "messages": [{"role": "user", "content": payload.prompt}],
        "max_tokens": payload.max_tokens,
        "temperature": payload.temperature,
    }
    routes = plan_routing_order(model)
    backend_errors: list[dict] = []
    started = time.perf_counter()
    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
        try:
            result = await proxy.chat(
                body,
                False,
                include_reasoning,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                prompt_template=model.prompt_template,
                is_admin=True,
            )
            response_payload = json.loads(result.response.body.decode("utf-8"))
            usage = response_payload.get("usage") or {}
            content = ""
            if response_payload.get("choices"):
                message = response_payload["choices"][0].get("message") or {}
                content = message.get("content") or ""
            return {
                "response": content,
                "raw_response": response_payload,
                "model_used": model.model_id,
                "backend_used": backend.name,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "tokens": usage,
                "attempts": attempt,
                "fallback_used": attempt > 1,
                "include_reasoning": include_reasoning,
                "prompt_template": model.prompt_template,
                "backend_errors": backend_errors,
            }
        except HTTPException as exc:
            backend_errors.append(
                {
                    "backend_name": backend.name if backend else None,
                    "backend_id": str(route.inference_backend_id),
                    "status_code": exc.status_code,
                    "error": exc.detail,
                }
            )
    raise HTTPException(
        status_code=503,
        detail={
            "message": "all backend routes failed",
            "backend_errors": backend_errors,
        },
    )


@router.post("/routing/explain", response_model=RoutingExplainResponse)
async def explain_routing(
    payload: RoutingExplainRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Explains the routing decision for a given model and client.
    """
    # Fetch Client with BillingPlan
    client = await session.get(Client, payload.client_id, options=[selectinload(Client.billing_plan)])
    if not client:
        raise HTTPException(status_code=404, detail="client not found")
        
    # Resolve Model
    selected_model, requested_model = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model or "default",
    )
    
    # Get all potential candidates
    all_candidates = get_routing_candidates(selected_model)
    
    # Analyze policy application
    routing_policy = None
    if client.billing_plan and client.billing_plan.routing_policy_json:
        try:
            routing_policy = json.loads(client.billing_plan.routing_policy_json)
        except json.JSONDecodeError:
            pass
            
    # Apply policy
    final_candidates = apply_routing_policy(selected_model, client, list(all_candidates))
    
    # Identify rejected candidates
    final_ids = {c.id for c in final_candidates}
    rejected = [c for c in all_candidates if c.id not in final_ids]
    
    def serialize_route(r):
        return {
            "backend_name": r.inference_backend.name,
            "backend_type": r.inference_backend.provider,
            "priority": r.priority,
            "weight": r.weight,
            "state": r.state,
        }

    return RoutingExplainResponse(
        requested_model=payload.model,
        resolved_model_id=str(selected_model.model_id),
        resolved_model_alias=selected_model.model_alias,
        client_name=client.name,
        plan_code=client.billing_plan.code if client.billing_plan else "free",
        routing_policy=routing_policy,
        chosen_backend=final_candidates[0].inference_backend.name if final_candidates else None,
        candidates_order=[serialize_route(c) for c in final_candidates],
        rejected_candidates=[serialize_route(c) for c in rejected],
    )


@router.post("/models/reload", response_model=ModelReloadResponse)
async def reload_models(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_model(session)
    await session.commit()
    await proxy.health()
    return ModelReloadResponse(
        status="accepted",
        detail="registry reloaded from configuration; for a new GGUF file, restart the data-plane container",
    )


@router.post("/test/clients/{client_id}/reset-usage")
async def reset_client_usage(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    if not settings.test_tools_enabled or settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    
    await session.execute(
        select(QuotaCounter).where(QuotaCounter.client_id == client_id)
    )
    # Delete all quota counters for this client to reset usage
    from sqlalchemy import delete
    await session.execute(delete(QuotaCounter).where(QuotaCounter.client_id == client_id))
    await session.execute(delete(UsageRecord).where(UsageRecord.client_id == client_id))
    await session.commit()
    return {"status": "reset", "client_id": str(client_id)}


@router.get("/test/commands", response_model=list[TestCommand])
async def list_test_commands():
    if not settings.test_tools_enabled or settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    return [
        TestCommand(id=k, name=v["name"], description=v["description"], command=v["command"])
        for k, v in WHITELISTED_COMMANDS.items()
    ]


@router.post("/test/run", response_model=TestRunResponse)
async def run_test_command(payload: TestRunRequest):
    if not settings.test_tools_enabled or settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    
    cmd_info = WHITELISTED_COMMANDS.get(payload.command_id)
    if not cmd_info:
        raise HTTPException(status_code=404, detail="command not found")
    
    start_time = time.time()
    run_id = str(uuid.uuid4())
    
    try:
        # Run command with 60s timeout
        # Using shell=True because we trust WHITELISTED_COMMANDS and it's local test only
        env = os.environ.copy()
        env["BASE_URL"] = "http://localhost:8080"

        result = subprocess.run(
            cmd_info["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parents[2]), # project root (/app)
            env=env
        )
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="completed" if result.returncode == 0 else "failed",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            duration_seconds=round(duration, 2),
            created_at=utc_now()
        )
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="timeout",
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "Timeout after 60s",
            exit_code=124,
            duration_seconds=round(duration, 2),
            created_at=utc_now()
        )
    except Exception as e:
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="error",
            stderr=str(e),
            exit_code=1,
            duration_seconds=round(duration, 2),
            created_at=utc_now()
        )

@router.get("/usage/{client_id}/summary")
async def get_client_usage_summary(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    from app.models.client import Client
    from app.models.usage_record import UsageRecord
    from sqlalchemy.orm import selectinload
    import datetime
    
    result = await session.execute(
        select(Client).options(selectinload(Client.billing_plan)).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    now = datetime.datetime.now(datetime.timezone.utc).date()
    today_start = now
    month_start = now.replace(day=1)
    
    usage_result = await session.execute(
        select(UsageRecord).where(
            UsageRecord.client_id == client_id,
            UsageRecord.period_start.in_([today_start, month_start])
        )
    )
    records = usage_result.scalars().all()
    
    today_record = next((r for r in records if r.period_type == "daily" and r.period_start == today_start), None)
    month_record = next((r for r in records if r.period_type == "monthly" and r.period_start == month_start), None)
    
    today_tokens = today_record.prompt_tokens + today_record.completion_tokens if today_record else 0
    today_requests = today_record.request_count if today_record else 0
    
    month_tokens = month_record.prompt_tokens + month_record.completion_tokens if month_record else 0
    month_requests = month_record.request_count if month_record else 0
    
    daily_quota = client.daily_token_quota
    monthly_quota = client.monthly_token_quota
    
    plan_cost = float(client.billing_plan.price_brl) if client.billing_plan else 0.0
    
    return {
        "client_id": str(client.id),
        "client_name": client.name,
        "plan_name": client.billing_plan.name if client.billing_plan else "None",
        "plan_cost_brl": plan_cost,
        "today": {
            "tokens_used": today_tokens,
            "requests": today_requests,
            "limit": daily_quota,
            "percent_used": round((today_tokens / daily_quota * 100) if daily_quota > 0 else 0, 2)
        },
        "month": {
            "tokens_used": month_tokens,
            "requests": month_requests,
            "limit": monthly_quota,
            "percent_used": round((month_tokens / monthly_quota * 100) if monthly_quota > 0 else 0, 2)
        }
    }
