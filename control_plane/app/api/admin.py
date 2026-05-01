import json
from datetime import date, datetime
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_inference_proxy
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
    BillingPlanCreate,
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
    ModelRegistryPatch,
    ModelReloadResponse,
    PricingRuleRead,
)
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
from app.services.backend_registry import ensure_default_backends
from app.services.auth import require_admin
from app.services.export_reporting import (
    build_monthly_report,
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
from app.services.model_policy import serialize_routing_table
from app.services.model_registry import ensure_default_model
from app.services.response_cache import clear_response_cache, get_response_cache_stats
from app.services.security_monitor import (
    list_security_events,
    observe_billing_status_metrics,
    suspend_client_for_security,
    unsuspend_client_for_security,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _serialize_api_key_created(api_key: ApiKey, plaintext: str) -> ApiKeyCreated:
    return ApiKeyCreated(
        id=api_key.id,
        client_id=api_key.client_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=plaintext,
        scopes=json.loads(api_key.scopes_json) if api_key.scopes_json else None,
        created_at=api_key.created_at,
    )


def _serialize_billing_plan_payload(payload: BillingPlanCreate) -> dict:
    plan_data = payload.model_dump()
    allowed_models = plan_data.pop("allowed_models", None)
    plan_data["allowed_models_json"] = json.dumps(allowed_models) if allowed_models is not None else None
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
    result = await session.execute(select(Client).order_by(Client.created_at.desc()))
    return result.scalars().all()


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
    )
    current_key.revoked_at = utc_now()
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
        select(ApiKey, Client.name.label("client_name"))
        .join(Client, Client.id == ApiKey.client_id)
        .order_by(desc(ApiKey.created_at))
        .limit(200)
    )
    rows = result.all()
    return [
        {
            "id": str(api_key.id),
            "client_id": str(api_key.client_id),
            "client_name": client_name,
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "created_at": api_key.created_at.isoformat(),
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None,
        }
        for api_key, client_name in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
async def revoke_api_key(api_key_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    api_key = await session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    api_key.revoked_at = utc_now()
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
async def get_usage_summary(session: AsyncSession = Depends(get_db_session)):
    await observe_billing_status_metrics(session)
    request_stats_query = (
        select(
            Client.id.label("client_id"),
            Client.name.label("client_name"),
            Client.is_blocked.label("is_blocked"),
            Client.billing_status.label("billing_status"),
            Client.billing_plan_id.label("billing_plan_id"),
            BillingPlan.code.label("billing_plan_code"),
            BillingPlan.name.label("billing_plan_name"),
            BillingPlan.rate_limit_per_minute.label("plan_rpm"),
            BillingPlan.daily_token_quota.label("plan_daily_token_quota"),
            BillingPlan.monthly_token_quota.label("plan_monthly_token_quota"),
            BillingPlan.max_output_tokens.label("plan_max_output_tokens"),
            BillingPlan.allow_streaming.label("plan_allow_streaming"),
            func.coalesce(func.sum(RequestLog.estimated_cost_usd), 0).label("estimated_cost_usd"),
            func.count(RequestLog.id).label("requests_total"),
            func.coalesce(func.sum(RequestLog.prompt_tokens_estimated), 0).label("prompt_tokens_estimated"),
            func.coalesce(func.sum(RequestLog.completion_tokens_estimated), 0).label("completion_tokens_estimated"),
            func.coalesce(func.sum(case((RequestLog.http_status >= 400, 1), else_=0)), 0).label("errors_total"),
            func.coalesce(func.avg(RequestLog.latency_ms), 0).label("avg_latency_ms"),
            func.max(RequestLog.created_at).label("last_request_at"),
        )
        .select_from(Client)
        .outerjoin(BillingPlan, BillingPlan.id == Client.billing_plan_id)
        .outerjoin(RequestLog, RequestLog.client_id == Client.id)
        .group_by(
            Client.id,
            Client.name,
            Client.is_blocked,
            Client.billing_status,
            Client.billing_plan_id,
            BillingPlan.code,
            BillingPlan.name,
            BillingPlan.rate_limit_per_minute,
            BillingPlan.daily_token_quota,
            BillingPlan.monthly_token_quota,
            BillingPlan.max_output_tokens,
            BillingPlan.allow_streaming,
        )
        .order_by(Client.created_at.desc())
    )
    request_stats = (await session.execute(request_stats_query)).mappings().all()

    usage_query = (
        select(
            UsageRecord.client_id.label("client_id"),
            func.coalesce(func.sum(UsageRecord.request_count), 0).label("usage_requests_total"),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("usage_prompt_tokens_total"),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("usage_completion_tokens_total"),
        )
        .group_by(UsageRecord.client_id)
    )
    usage_rows = {
        row["client_id"]: row for row in (await session.execute(usage_query)).mappings().all()
    }
    pricing_rules = {
        row.billing_plan_id: row
        for row in (await session.execute(select(PricingRule).where(PricingRule.is_active.is_(True)))).scalars().all()
    }

    clients: list[dict] = []
    totals = {
        "clients_total": len(request_stats),
        "requests_total": 0,
        "tokens_estimated_total": 0,
        "errors_total": 0,
        "avg_latency_ms": 0.0,
        "estimated_cost_usd": 0.0,
    }
    by_plan: dict[str, dict] = {}
    latency_sum = 0.0
    latency_clients = 0
    for row in request_stats:
        usage_row = usage_rows.get(row["client_id"])
        client_stub = Client(
            id=row["client_id"],
            name=row["client_name"],
            is_blocked=row["is_blocked"],
            billing_status=row["billing_status"],
            description=None,
            billing_plan_id=None,
            rate_limit_per_minute=5,
            daily_token_quota=20_000,
            monthly_token_quota=300_000,
            max_context_tokens=4096,
            max_output_tokens=2048,
            metadata_json=None,
        )
        if row["billing_plan_code"] is not None:
            plan_stub = BillingPlan(
                code=row["billing_plan_code"],
                name=row["billing_plan_name"],
                description=None,
                rate_limit_per_minute=int(row["plan_rpm"]),
                daily_token_quota=int(row["plan_daily_token_quota"]),
                monthly_token_quota=int(row["plan_monthly_token_quota"]),
                max_output_tokens=int(row["plan_max_output_tokens"]),
                allow_streaming=bool(row["plan_allow_streaming"]),
                is_active=True,
            )
            pricing_rule = pricing_rules.get(row["billing_plan_id"])
            if pricing_rule is not None:
                plan_stub.pricing_rules = [pricing_rule]
            client_stub.billing_plan = plan_stub
        effective_plan = resolve_effective_plan(client_stub)
        counters = await get_current_usage_snapshot(session, row["client_id"])
        daily_used = int(counters["daily"].used_tokens) if counters["daily"] else 0
        monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
        total_tokens_estimated = int(row["prompt_tokens_estimated"] + row["completion_tokens_estimated"])
        invoice_preview = build_invoice_preview(
            effective_plan=effective_plan,
            monthly_used_tokens=monthly_used,
        )
        client_entry = {
            "client_id": str(row["client_id"]),
            "name": row["client_name"],
            "is_blocked": row["is_blocked"],
            "billing_status": row["billing_status"],
            "billing_plan_code": effective_plan.code,
            "billing_plan_name": effective_plan.name,
            "plan_limits": {
                "rate_limit_per_minute": effective_plan.rate_limit_per_minute,
                "daily_token_quota": effective_plan.daily_token_quota,
                "monthly_token_quota": effective_plan.monthly_token_quota,
                "max_output_tokens": effective_plan.max_output_tokens,
                "allow_streaming": effective_plan.allow_streaming,
            },
            "requests_total": int(row["requests_total"] or 0),
            "tokens_estimated_total": total_tokens_estimated,
            "estimated_cost_usd": round(float(row["estimated_cost_usd"] or 0), 6),
            "prompt_tokens_estimated": int(row["prompt_tokens_estimated"] or 0),
            "completion_tokens_estimated": int(row["completion_tokens_estimated"] or 0),
            "errors_total": int(row["errors_total"] or 0),
            "avg_latency_ms": round(float(row["avg_latency_ms"] or 0), 2),
            "last_request_at": row["last_request_at"].isoformat() if row["last_request_at"] else None,
            "usage_record_requests_total": int(usage_row["usage_requests_total"]) if usage_row else 0,
            "usage_record_tokens_total": int((usage_row["usage_prompt_tokens_total"] + usage_row["usage_completion_tokens_total"])) if usage_row else 0,
            "daily_usage": {
                "used_tokens": daily_used,
                "remaining_tokens": max(effective_plan.daily_token_quota - daily_used, 0),
            },
            "monthly_usage": {
                "used_tokens": monthly_used,
                "remaining_tokens": max(effective_plan.monthly_token_quota - monthly_used, 0),
            },
            "invoice_preview": invoice_preview,
        }
        clients.append(client_entry)
        plan_bucket = by_plan.setdefault(
            effective_plan.code,
            {
                "billing_plan_code": effective_plan.code,
                "billing_plan_name": effective_plan.name,
                "clients_total": 0,
                "requests_total": 0,
                "tokens_estimated_total": 0,
                "errors_total": 0,
                "daily_used_tokens": 0,
                "monthly_used_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
        )
        plan_bucket["clients_total"] += 1
        plan_bucket["requests_total"] += client_entry["requests_total"]
        plan_bucket["tokens_estimated_total"] += client_entry["tokens_estimated_total"]
        plan_bucket["errors_total"] += client_entry["errors_total"]
        plan_bucket["daily_used_tokens"] += daily_used
        plan_bucket["monthly_used_tokens"] += monthly_used
        plan_bucket["estimated_cost_usd"] += invoice_preview["total_estimated"]
        totals["requests_total"] += client_entry["requests_total"]
        totals["tokens_estimated_total"] += client_entry["tokens_estimated_total"]
        totals["errors_total"] += client_entry["errors_total"]
        totals["estimated_cost_usd"] += invoice_preview["total_estimated"]
        if client_entry["requests_total"] > 0:
            latency_sum += client_entry["avg_latency_ms"]
            latency_clients += 1
    if latency_clients > 0:
        totals["avg_latency_ms"] = round(latency_sum / latency_clients, 2)
    totals["estimated_cost_usd"] = round(totals["estimated_cost_usd"], 6)
    for item in by_plan.values():
        item["estimated_cost_usd"] = round(item["estimated_cost_usd"], 6)

    return {
        "generated_at": utc_now().isoformat(),
        "totals": totals,
        "plans": list(by_plan.values()),
        "clients": clients,
    }


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


@router.get("/billing/invoices/preview")
async def preview_invoices(session: AsyncSession = Depends(get_db_session)):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session)
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
async def preview_client_invoice(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session)
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
        .options(
            selectinload(ModelRegistry.inference_backend),
            selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
        )
        .order_by(ModelRegistry.created_at.desc())
    )
    registry = result.scalars().all()
    backends = (
        await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))
    ).scalars().all()
    plans = (await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))).scalars().all()
    return {
        "registry": [
            {
                "id": str(item.id),
                "model_id": item.model_id,
                "model_alias": item.model_alias,
                "inference_backend_id": str(item.inference_backend_id) if item.inference_backend_id else None,
                "backend_name": item.inference_backend.name if item.inference_backend else None,
                "backend_url": item.inference_backend.backend_url if item.inference_backend else None,
                "provider": item.provider,
                "model_file": item.model_file,
                "status": item.status,
                "is_active": item.is_active,
                "is_default": item.is_default,
                "context_length": item.context_length,
                "metadata_json": item.metadata_json,
                "routes": serialize_routing_table(item),
            }
            for item in registry
        ],
        "plan_access": [
            {
                "billing_plan_id": str(plan.id),
                "billing_plan_code": plan.code,
                "allowed_models_json": plan.allowed_models_json,
            }
            for plan in plans
        ],
        "backends": [await proxy.health_backend(item) for item in backends],
    }


@router.get("/backends")
async def list_backends(session: AsyncSession = Depends(get_db_session)):
    await ensure_default_backends(session)
    await session.commit()
    rows = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "provider": item.provider,
            "backend_url": item.backend_url,
            "healthcheck_path": item.healthcheck_path,
            "is_active": item.is_active,
            "is_default": item.is_default,
            "status": item.status,
            "max_parallel_requests": item.max_parallel_requests,
            "current_running": item.current_running,
            "metadata_json": item.metadata_json,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in rows
    ]


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
            .options(
                selectinload(ModelRegistry.inference_backend),
                selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
            )
            .order_by(ModelRegistry.created_at.asc())
        )
    ).scalars().all()
    model_rows = []
    summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "disabled": 0}
    for item in models:
        routes = serialize_routing_table(item)
        for route in routes:
            summary[route["state"]] = summary.get(route["state"], 0) + 1
            route["health"] = backend_health.get(route["backend_id"], {}).get("ok")
            route["latency_ms"] = backend_health.get(route["backend_id"], {}).get("latency_ms")
        model_rows.append(
            {
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


@router.post("/models", status_code=201)
async def create_model(payload: ModelRegistryCreate, session: AsyncSession = Depends(get_db_session)):
    if payload.inference_backend_id is not None and await session.get(InferenceBackend, payload.inference_backend_id) is None:
        raise HTTPException(status_code=404, detail="backend not found")
    clauses = [ModelRegistry.model_id == payload.model_id]
    if payload.model_alias:
        clauses.append(ModelRegistry.model_alias == payload.model_alias)
    existing = await session.execute(select(ModelRegistry).where(or_(*clauses)))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="model id or alias already exists")
    if payload.is_default:
        defaults = (await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True)))).scalars().all()
        for item in defaults:
            item.is_default = False
    model_payload = payload.model_dump(exclude={"backend_routes"})
    model = ModelRegistry(**model_payload)
    session.add(model)
    await session.flush()
    if payload.backend_routes:
        await _sync_model_backend_routes(
            session,
            model,
            [item.model_dump() for item in payload.backend_routes],
        )
    await session.commit()
    await session.refresh(model, attribute_names=["backend_routes", "inference_backend"])
    return {
        "id": str(model.id),
        "model_id": model.model_id,
        "model_alias": model.model_alias,
        "inference_backend_id": str(model.inference_backend_id) if model.inference_backend_id else None,
        "provider": model.provider,
        "model_file": model.model_file,
        "status": model.status,
        "is_active": model.is_active,
        "is_default": model.is_default,
        "context_length": model.context_length,
        "metadata_json": model.metadata_json,
        "routes": serialize_routing_table(model),
    }


@router.patch("/models/{model_id}")
async def patch_model(
    model_id: uuid.UUID,
    payload: ModelRegistryPatch,
    session: AsyncSession = Depends(get_db_session),
):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    patch_data = payload.model_dump(exclude_unset=True)
    routes_payload = patch_data.pop("backend_routes", None)
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
        defaults = (await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True), ModelRegistry.id != model_id))).scalars().all()
        for item in defaults:
            item.is_default = False
    for key, value in patch_data.items():
        setattr(model, key, value)
    if routes_payload is not None:
        await _sync_model_backend_routes(session, model, routes_payload)
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model, attribute_names=["backend_routes", "inference_backend"])
    return {
        "id": str(model.id),
        "model_id": model.model_id,
        "model_alias": model.model_alias,
        "inference_backend_id": str(model.inference_backend_id) if model.inference_backend_id else None,
        "provider": model.provider,
        "model_file": model.model_file,
        "status": model.status,
        "is_active": model.is_active,
        "is_default": model.is_default,
        "context_length": model.context_length,
        "metadata_json": model.metadata_json,
        "routes": serialize_routing_table(model),
    }


@router.post("/models/{model_id}/enable")
async def enable_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    model.is_active = True
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
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "disabled", "id": str(model.id)}


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
