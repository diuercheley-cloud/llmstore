from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.core.time import utc_now
from app.models.billing.billing_invoice import BillingInvoice
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.billing.customer_payment import CustomerPayment
from app.models.billing.pricing_rule import PricingRule
from app.models.core.quota_counter import QuotaCounter
from app.services.quota import month_start
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


@dataclass
class EffectivePlan:
    code: str
    name: str
    rate_limit_per_minute: int
    daily_token_quota: int
    weekly_token_quota: int
    monthly_token_quota: int
    max_output_tokens: int
    allow_streaming: bool
    max_context_tokens: int = 4096
    monthly_price: Decimal = Decimal("0")
    overage_price_per_1k_tokens: Decimal = Decimal("0")
    currency: str = "USD"
    # Request Limits
    requests_per_day: int = 0
    requests_per_month: int = 0
    # RAG
    rag_enabled: bool = False
    rag_max_documents: int | None = None
    rag_max_storage_mb: int | None = None
    rag_max_pages_per_month: int | None = None
    rag_max_queries_per_month: int | None = None
    # TTS Limits
    tts_enabled: bool = False
    tts_chars_per_request: int = 500
    tts_chars_per_day: int = 5000
    tts_chars_per_month: int = 50000
    tts_audio_retention_days: int = 7
    tts_max_files: int = 100
    # Embeddings Limits
    embeddings_enabled: bool = False
    embeddings_requests_per_month: int = 0
    embeddings_tokens_per_month: int = 0
    embeddings_max_inputs_per_request: int = 16
    # Feature Gates
    responses_enabled: bool = True
    tools_enabled: bool = False
    export_enabled: bool = False
    support_level: str = "Community"


DEFAULT_BILLING_PLANS = [
    {
        "code": "free",
        "name": "Free",
        "description": "Starter plan for sandbox usage with strict limits and no card required.",
        "rate_limit_per_minute": 60,
        "daily_token_quota": 5000,
        "weekly_token_quota": 25000,
        "monthly_token_quota": 50000,
        "max_output_tokens": 32768,
        "allow_streaming": False,
        "rag_enabled": True,
        "rag_max_documents": 5,
        "rag_max_storage_mb": 50,
        "rag_max_pages_per_month": 100,
        "rag_max_queries_per_month": 50,
        "tts_enabled": True,
        "tts_chars_per_request": 1000,
        "tts_chars_per_day": 5000,
        "tts_chars_per_month": 50000,
        "embeddings_enabled": True,
        "embeddings_requests_per_month": 100,
        "embeddings_tokens_per_month": 100000,
        "embeddings_max_inputs_per_request": 8,
    },
    {
        "code": "basic",
        "name": "Basic",
        "description": "Production starter with streaming and predictable shared capacity.",
        "rate_limit_per_minute": 15,
        "daily_token_quota": 75000,
        "weekly_token_quota": 350000,
        "monthly_token_quota": 750000,
        "max_output_tokens": 32768,
        "allow_streaming": True,
        "rag_enabled": True,
        "rag_max_documents": 10,
        "rag_max_storage_mb": 100,
        "rag_max_pages_per_month": 500,
        "rag_max_queries_per_month": 100,
        "tts_enabled": True,
        "tts_chars_per_request": 500,
        "tts_chars_per_day": 2000,
        "tts_chars_per_month": 10000,
        "embeddings_enabled": True,
        "embeddings_requests_per_month": 1000,
        "embeddings_tokens_per_month": 1000000,
        "embeddings_max_inputs_per_request": 16,
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Growth plan with higher throughput for customer-facing workloads.",
        "rate_limit_per_minute": 45,
        "daily_token_quota": 300000,
        "weekly_token_quota": 1500000,
        "monthly_token_quota": 4000000,
        "max_output_tokens": 32768,
        "allow_streaming": True,
        "rag_enabled": True,
        "rag_max_documents": 100,
        "rag_max_storage_mb": 2048,
        "rag_max_pages_per_month": 5000,
        "rag_max_queries_per_month": 2000,
        "tts_enabled": True,
        "tts_chars_per_request": 2000,
        "tts_chars_per_day": 10000,
        "tts_chars_per_month": 100000,
        "embeddings_enabled": True,
        "embeddings_requests_per_month": 5000,
        "embeddings_tokens_per_month": 10000000,
        "embeddings_max_inputs_per_request": 32,
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "High-volume plan for dedicated routing, premium support and custom rollout.",
        "rate_limit_per_minute": 120,
        "daily_token_quota": 1500000,
        "weekly_token_quota": 7000000,
        "monthly_token_quota": 15000000,
        "max_output_tokens": 32768,
        "allow_streaming": True,
        "rag_enabled": True,
        "rag_max_documents": None,
        "rag_max_storage_mb": None,
        "rag_max_pages_per_month": None,
        "rag_max_queries_per_month": None,
        "tts_enabled": True,
        "tts_chars_per_request": 10000,
        "tts_chars_per_day": 100000,
        "tts_chars_per_month": 1000000,
        "embeddings_enabled": True,
        "embeddings_requests_per_month": 50000,
        "embeddings_tokens_per_month": 100000000,
        "embeddings_max_inputs_per_request": 128,
    },
]

DEFAULT_PRICING_RULES = {
    "free": {
        "currency": "USD",
        "monthly_price": Decimal("0"),
        "overage_price_per_1k_tokens": Decimal("0.000000"),
        "description": "Free plan with hard limits and no overage.",
    },
    "basic": {
        "currency": "USD",
        "monthly_price": Decimal("29.0000"),
        "overage_price_per_1k_tokens": Decimal("0.040000"),
        "description": "Starter paid plan.",
    },
    "pro": {
        "currency": "USD",
        "monthly_price": Decimal("99.0000"),
        "overage_price_per_1k_tokens": Decimal("0.030000"),
        "description": "Growth plan with better unit economics.",
    },
    "enterprise": {
        "currency": "USD",
        "monthly_price": Decimal("399.0000"),
        "overage_price_per_1k_tokens": Decimal("0.025000"),
        "description": "Dedicated enterprise rollout.",
    },
}

INVOICE_STATUSES = {"pending", "paid", "overdue", "cancelled"}
CLIENT_BILLING_STATUSES = {"active", "past_due", "suspended"}
MANUAL_PIX_PAYMENT_METHOD = "manual_pix"


async def ensure_default_billing_plans(session: AsyncSession) -> dict[str, BillingPlan]:
    existing = {
        plan.code: plan
        for plan in (await session.execute(select(BillingPlan))).scalars().all()
    }
    for payload in DEFAULT_BILLING_PLANS:
        plan = existing.get(payload["code"])
        if plan is None:
            plan = BillingPlan(**payload)
            session.add(plan)
            await session.flush()
            existing[plan.code] = plan
            continue
        for key, value in payload.items():
            setattr(plan, key, value)
    return existing


async def ensure_default_pricing_rules(session: AsyncSession, plans: dict[str, BillingPlan]) -> dict[str, PricingRule]:
    existing = {
        row.billing_plan_id: row
        for row in (await session.execute(select(PricingRule).where(PricingRule.is_active.is_(True)))).scalars().all()
    }
    created_or_updated: dict[str, PricingRule] = {}
    for code, payload in DEFAULT_PRICING_RULES.items():
        plan = plans[code]
        rule = existing.get(plan.id)
        if rule is None:
            rule = PricingRule(billing_plan_id=plan.id, **payload)
            session.add(rule)
            await session.flush()
        else:
            for key, value in payload.items():
                setattr(rule, key, value)
        created_or_updated[code] = rule
    return created_or_updated


def month_window(reference_date: date) -> tuple[date, date]:
    end_day = monthrange(reference_date.year, reference_date.month)[1]
    start = reference_date.replace(day=1)
    end = reference_date.replace(day=end_day)
    return start, end


def previous_month_date(reference_date: date) -> date:
    previous_month_last_day = reference_date.replace(day=1) - timedelta(days=1)
    return previous_month_last_day


def should_generate_monthly_invoices(reference_date: date, invoice_day: int) -> bool:
    return reference_date.day == invoice_day


def normalize_invoice_status(status: str, due_at: datetime | None, *, now: datetime | None = None) -> str:
    if status != "pending" or due_at is None:
        return status
    current = now or utc_now()
    if due_at < current:
        return "overdue"
    return status


def derive_client_billing_status(
    *,
    has_overdue_invoice: bool,
    should_suspend: bool,
) -> str:
    if should_suspend:
        return "suspended"
    if has_overdue_invoice:
        return "past_due"
    return "active"


def _min_quota(a: int | None, b: int | None) -> int:
    if a is None and b is None:
        return 0
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def resolve_effective_plan(client: Client) -> EffectivePlan:
    if client.billing_plan is not None:
        plan = client.billing_plan
        pricing_rule = next((item for item in plan.pricing_rules if item.is_active), None)
        return EffectivePlan(
            code=plan.code,
            name=plan.name,
            rate_limit_per_minute=_min_quota(plan.rate_limit_per_minute, client.rate_limit_per_minute),
            daily_token_quota=_min_quota(plan.daily_token_quota, client.daily_token_quota),
            weekly_token_quota=_min_quota(plan.weekly_token_quota, client.weekly_token_quota),
            monthly_token_quota=_min_quota(plan.monthly_token_quota, client.monthly_token_quota),
            max_output_tokens=_min_quota(plan.max_output_tokens, client.max_output_tokens),
            max_context_tokens=_min_quota(getattr(plan, "max_context_tokens", 4096), client.max_context_tokens),
            allow_streaming=plan.allow_streaming,
            monthly_price=pricing_rule.monthly_price if pricing_rule else Decimal("0"),
            overage_price_per_1k_tokens=pricing_rule.overage_price_per_1k_tokens if pricing_rule else Decimal("0"),
            currency=pricing_rule.currency if pricing_rule else "USD",
            requests_per_day=getattr(plan, "requests_per_day", 0),
            requests_per_month=getattr(plan, "requests_per_month", 0),
            rag_enabled=getattr(plan, "rag_enabled", False),
            rag_max_documents=getattr(plan, "rag_max_documents", 5),
            rag_max_storage_mb=getattr(plan, "rag_max_storage_mb", 50),
            rag_max_pages_per_month=getattr(plan, "rag_max_pages_per_month", 100),
            rag_max_queries_per_month=getattr(plan, "rag_max_queries_per_month", 50),
            # TTS
            tts_enabled=getattr(plan, "tts_enabled", False),
            tts_chars_per_request=getattr(plan, "tts_chars_per_request", 0),
            tts_chars_per_day=getattr(plan, "tts_chars_per_day", 0),
            tts_chars_per_month=getattr(plan, "tts_chars_per_month", 0),
            tts_audio_retention_days=getattr(plan, "tts_audio_retention_days", 0),
            tts_max_files=getattr(plan, "tts_max_files", 0),
            # Embeddings
            embeddings_enabled=getattr(plan, "embeddings_enabled", False),
            embeddings_requests_per_month=getattr(plan, "embeddings_requests_per_month", 0),
            embeddings_tokens_per_month=getattr(plan, "embeddings_tokens_per_month", 0),
            embeddings_max_inputs_per_request=getattr(plan, "embeddings_max_inputs_per_request", 16),
            # Feature Gates
            responses_enabled=getattr(plan, "responses_enabled", True),
            tools_enabled=getattr(plan, "tools_enabled", False),
            export_enabled=getattr(plan, "export_enabled", False),
            support_level=getattr(plan, "support_level", "Community"),
        )
    return EffectivePlan(
        code="legacy",
        name="Legacy",
        rate_limit_per_minute=client.rate_limit_per_minute,
        daily_token_quota=client.daily_token_quota,
        weekly_token_quota=client.weekly_token_quota,
        monthly_token_quota=client.monthly_token_quota,
        max_output_tokens=client.max_output_tokens,
        max_context_tokens=client.max_context_tokens,
        allow_streaming=True,
        rag_enabled=True,
        rag_max_documents=5,
        rag_max_storage_mb=50,
        rag_max_pages_per_month=100,
        rag_max_queries_per_month=50,
        # TTS legacy defaults
        tts_enabled=False,
        tts_chars_per_request=0,
        tts_chars_per_day=0,
        tts_chars_per_month=0,
        # Embeddings legacy defaults
        embeddings_enabled=False,
        embeddings_requests_per_month=0,
        embeddings_tokens_per_month=0,
        embeddings_max_inputs_per_request=16,
        monthly_price=Decimal("0"),
        overage_price_per_1k_tokens=Decimal("0"),
        currency="USD",
        responses_enabled=True,
        tools_enabled=False,
        export_enabled=False,
        support_level="Community",
    )


async def resolve_effective_plan_for_session(session: AsyncSession, client: Client) -> EffectivePlan:
    """
    Resolves the effective plan after eagerly loading billing_plan and pricing_rules.
    This avoids async lazy-loading failures in request/runtime paths.
    """
    from sqlalchemy.orm import selectinload

    if client is None:
        return EffectivePlan(
            code="legacy",
            name="Legacy",
            rate_limit_per_minute=0,
            daily_token_quota=0,
            weekly_token_quota=0,
            monthly_token_quota=0,
            max_output_tokens=0,
            allow_streaming=True,
        )

    if "billing_plan" not in client.__dict__ or "pricing_rules" not in getattr(client.billing_plan, "__dict__", {}):
        result = await session.execute(
            select(Client)
            .options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules))
            .where(Client.id == client.id)
        )
        loaded = result.scalar_one_or_none()
        if loaded is not None:
            client = loaded

    return resolve_effective_plan(client)


async def list_client_billing_snapshots(
    session: AsyncSession,
    client_id=None,
    usage_reference_date: date | None = None,
) -> list[dict]:
    query = select(Client).options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules)).order_by(Client.created_at.desc())
    if client_id is not None:
        query = query.where(Client.id == client_id)
    clients = (await session.execute(query)).scalars().all()
    snapshots: list[dict] = []
    usage_date = usage_reference_date or date.today()
    for client in clients:
        effective_plan = resolve_effective_plan(client)
        counters = await get_usage_snapshot_for_date(session, client.id, usage_date)
        daily_used = int(counters["daily"].used_tokens) if counters["daily"] else 0
        weekly_used = int(counters["weekly"].used_tokens) if counters["weekly"] else 0
        monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
        
        # TTS usage
        daily_tts_used = int(counters["daily"].used_tts_chars) if counters["daily"] else 0
        monthly_tts_used = int(counters["monthly"].used_tts_chars) if counters["monthly"] else 0

        # Embeddings usage
        monthly_embeddings_requests = int(counters["monthly"].used_embeddings_requests) if counters["monthly"] else 0
        monthly_embeddings_tokens = int(counters["monthly"].used_embeddings_tokens) if counters["monthly"] else 0

        pricing_rule = None
        if client.billing_plan is not None:
            pricing_rule = next((item for item in client.billing_plan.pricing_rules if item.is_active), None)
        snapshots.append(
            {
                "client": client,
                "effective_plan": effective_plan,
                "pricing_rule": pricing_rule,
                "daily_used_tokens": daily_used,
                "weekly_used_tokens": weekly_used,
                "monthly_used_tokens": monthly_used,
                "daily_used_tts_chars": daily_tts_used,
                "monthly_used_tts_chars": monthly_tts_used,
                "monthly_used_embeddings_requests": monthly_embeddings_requests,
                "monthly_used_embeddings_tokens": monthly_embeddings_tokens,
                "invoice_preview": build_invoice_preview(
                    effective_plan=effective_plan,
                    monthly_used_tokens=monthly_used,
                    monthly_used_tts_chars=monthly_tts_used,
                    monthly_used_embeddings_requests=monthly_embeddings_requests,
                    monthly_used_embeddings_tokens=monthly_embeddings_tokens,
                ),
            }
        )
    return snapshots


async def get_usage_snapshot_for_date(session: AsyncSession, client_id, reference_date: date) -> dict[str, QuotaCounter | None]:
    from app.services.quota import week_start
    period_pairs = {
        "daily": reference_date,
        "weekly": week_start(reference_date),
        "monthly": month_start(reference_date),
    }
    snapshot: dict[str, QuotaCounter | None] = {"daily": None, "weekly": None, "monthly": None}
    for period_type, period_start in period_pairs.items():
        result = await session.execute(
            select(QuotaCounter).where(
                QuotaCounter.client_id == client_id,
                QuotaCounter.period_type == period_type,
                QuotaCounter.period_start == period_start,
            )
        )
        snapshot[period_type] = result.scalar_one_or_none()
    return snapshot


async def get_current_usage_snapshot(session: AsyncSession, client_id) -> dict[str, QuotaCounter | None]:
    return await get_usage_snapshot_for_date(session, client_id, date.today())


def estimate_request_cost(monthly_tokens_used_before: int, request_tokens: int, included_monthly_tokens: int, overage_price_per_1k_tokens: Decimal) -> Decimal:
    before_overage = max(monthly_tokens_used_before - included_monthly_tokens, 0)
    after_overage = max(monthly_tokens_used_before + request_tokens - included_monthly_tokens, 0)
    marginal_overage_tokens = max(after_overage - before_overage, 0)
    if marginal_overage_tokens <= 0:
        return Decimal("0")
    return ((Decimal(marginal_overage_tokens) / Decimal(1000)) * overage_price_per_1k_tokens).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )


def build_invoice_preview(*, effective_plan: EffectivePlan, monthly_used_tokens: int, monthly_used_tts_chars: int = 0, monthly_used_embeddings_requests: int = 0, monthly_used_embeddings_tokens: int = 0) -> dict:
    included_tokens = effective_plan.monthly_token_quota
    overage_tokens = max(monthly_used_tokens - included_tokens, 0)
    overage_cost = ((Decimal(overage_tokens) / Decimal(1000)) * effective_plan.overage_price_per_1k_tokens).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    
    # Simulated TTS overage (just for show in preview for now)
    tts_included = effective_plan.tts_chars_per_month
    tts_overage = max(monthly_used_tts_chars - tts_included, 0)

    # Embeddings usage in preview
    emb_req_included = effective_plan.embeddings_requests_per_month
    emb_tokens_included = effective_plan.embeddings_tokens_per_month
    emb_req_overage = max(monthly_used_embeddings_requests - emb_req_included, 0)
    emb_tokens_overage = max(monthly_used_embeddings_tokens - emb_tokens_included, 0)
    
    total_estimated = (effective_plan.monthly_price + overage_cost).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return {
        "currency": effective_plan.currency,
        "monthly_price": float(effective_plan.monthly_price),
        "included_tokens": included_tokens,
        "used_tokens": monthly_used_tokens,
        "overage_tokens": overage_tokens,
        "overage_price_per_1k_tokens": float(effective_plan.overage_price_per_1k_tokens),
        "overage_cost": float(overage_cost),
        "tts_chars_included": tts_included,
        "tts_chars_used": monthly_used_tts_chars,
        "tts_overage": tts_overage,
        "embeddings_requests_included": emb_req_included,
        "embeddings_requests_used": monthly_used_embeddings_requests,
        "embeddings_requests_overage": emb_req_overage,
        "embeddings_tokens_included": emb_tokens_included,
        "embeddings_tokens_used": monthly_used_embeddings_tokens,
        "embeddings_tokens_overage": emb_tokens_overage,
        "total_estimated": float(total_estimated),
    }


def build_invoice_record_data(
    *,
    client: Client,
    effective_plan: EffectivePlan,
    pricing_rule: PricingRule | None,
    monthly_used_tokens: int,
    monthly_used_tts_chars: int = 0,
    monthly_used_embeddings_requests: int = 0,
    monthly_used_embeddings_tokens: int = 0,
    period_reference: date,
    due_in_days: int,
    payment_method: str,
    payment_instructions: str | None,
    now: datetime | None = None,
) -> dict:
    period_start, period_end = month_window(period_reference)
    preview = build_invoice_preview(
        effective_plan=effective_plan, 
        monthly_used_tokens=monthly_used_tokens,
        monthly_used_tts_chars=monthly_used_tts_chars,
        monthly_used_embeddings_requests=monthly_used_embeddings_requests,
        monthly_used_embeddings_tokens=monthly_used_embeddings_tokens,
    )
    created_at = now or utc_now()
    due_at = created_at + timedelta(days=due_in_days)
    return {
        "client_id": client.id,
        "billing_plan_id": client.billing_plan_id,
        "pricing_rule_id": pricing_rule.id if pricing_rule else None,
        "status": "pending",
        "currency": preview["currency"],
        "period_start": period_start,
        "period_end": period_end,
        "monthly_price": Decimal(str(preview["monthly_price"])),
        "included_tokens": preview["included_tokens"],
        "used_tokens": preview["used_tokens"],
        "overage_tokens": preview["overage_tokens"],
        "overage_price_per_1k_tokens": Decimal(str(preview["overage_price_per_1k_tokens"])),
        "overage_cost": Decimal(str(preview["overage_cost"])),
        "total_amount": Decimal(str(preview["total_estimated"])),
        "payment_method": payment_method,
        "payment_instructions": payment_instructions,
        "due_at": due_at,
        "paid_at": None,
        "cancelled_at": None,
    }


async def refresh_billing_statuses(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    suspend_after_days: int = 15,
) -> dict[str, int]:
    current_time = now or utc_now()
    updated_invoices = 0
    overdue_invoices = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.payments))
            .where(
                BillingInvoice.status == "pending",
                BillingInvoice.due_at.is_not(None),
                BillingInvoice.due_at < current_time,
            )
        )
    ).scalars().all()
    for invoice in overdue_invoices:
        invoice.status = "overdue"
        invoice.updated_at = current_time
        for payment in invoice.payments:
            if payment.status == "pending":
                payment.status = "overdue"
                payment.updated_at = current_time
        updated_invoices += 1

    client_rows = (
        await session.execute(
            select(Client).options(selectinload(Client.invoices), selectinload(Client.payments))
        )
    ).scalars().all()
    updated_clients = 0
    for client in client_rows:
        overdue_invoices_for_client = [item for item in client.invoices if item.status == "overdue"]
        has_overdue = bool(overdue_invoices_for_client)
        should_suspend = False
        for item in overdue_invoices_for_client:
            if item.due_at is not None:
                due_at = item.due_at
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
                if due_at + timedelta(days=suspend_after_days) < current_time:
                    should_suspend = True
                    break
        next_status = derive_client_billing_status(
            has_overdue_invoice=has_overdue,
            should_suspend=should_suspend,
        )
        if next_status != client.billing_status:
            client.billing_status = next_status
            client.updated_at = current_time
            updated_clients += 1

    return {"updated_invoices": updated_invoices, "updated_clients": updated_clients}


async def generate_monthly_invoices(
    session: AsyncSession,
    *,
    reference_datetime: datetime | None = None,
    invoice_day: int,
    due_in_days: int,
    suspend_after_days: int,
    payment_method: str = MANUAL_PIX_PAYMENT_METHOD,
    payment_instructions: str | None = None,
    force: bool = False,
    client_id=None,
) -> dict:
    current_time = reference_datetime or utc_now()
    today = current_time.date()
    if not force and not should_generate_monthly_invoices(today, invoice_day):
        return {
            "generated_at": current_time.isoformat(),
            "created": [],
            "updated": [],
            "skipped": [],
            "reason": "invoice day not reached",
        }

    billing_period_reference = previous_month_date(today)
    snapshots = await list_client_billing_snapshots(
        session,
        client_id=client_id,
        usage_reference_date=billing_period_reference,
    )
    created = []
    updated = []
    skipped = []
    for snapshot in snapshots:
        client = snapshot["client"]
        invoice_data = build_invoice_record_data(
            client=client,
            effective_plan=snapshot["effective_plan"],
            pricing_rule=snapshot["pricing_rule"],
            monthly_used_tokens=snapshot["monthly_used_tokens"],
            monthly_used_tts_chars=snapshot.get("monthly_used_tts_chars", 0),
            period_reference=billing_period_reference,
            due_in_days=due_in_days,
            payment_method=payment_method,
            payment_instructions=payment_instructions,
            now=current_time,
        )
        existing = (
            await session.execute(
                select(BillingInvoice)
                .options(selectinload(BillingInvoice.payments))
                .where(
                    BillingInvoice.client_id == client.id,
                    BillingInvoice.period_start == invoice_data["period_start"],
                    BillingInvoice.period_end == invoice_data["period_end"],
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            invoice = BillingInvoice(**invoice_data)
            session.add(invoice)
            await session.flush()
            session.add(
                CustomerPayment(
                    invoice_id=invoice.id,
                    client_id=client.id,
                    status=invoice.status,
                    amount=invoice.total_amount,
                    currency=invoice.currency,
                    payment_method=invoice.payment_method,
                    note=invoice.payment_instructions,
                )
            )
            created.append(invoice)
            continue
        if existing.status in {"paid", "cancelled"}:
            skipped.append({"invoice_id": str(existing.id), "client_id": str(client.id), "status": existing.status})
            continue
        for key, value in invoice_data.items():
            if key not in {"client_id", "period_start", "period_end"}:
                setattr(existing, key, value)
        pending_payment = next((item for item in existing.payments if item.status in {"pending", "overdue"}), None)
        if pending_payment is None:
            session.add(
                CustomerPayment(
                    invoice_id=existing.id,
                    client_id=client.id,
                    status=existing.status,
                    amount=existing.total_amount,
                    currency=existing.currency,
                    payment_method=existing.payment_method,
                    note=existing.payment_instructions,
                )
            )
        else:
            pending_payment.status = existing.status
            pending_payment.amount = existing.total_amount
            pending_payment.currency = existing.currency
            pending_payment.payment_method = existing.payment_method
            pending_payment.note = existing.payment_instructions
            pending_payment.updated_at = current_time
        updated.append(existing)

    await refresh_billing_statuses(
        session,
        now=current_time,
        suspend_after_days=suspend_after_days,
    )
    return {
        "generated_at": current_time.isoformat(),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "reason": None,
    }


def serialize_invoice(invoice: BillingInvoice) -> dict:
    return {
        "id": str(invoice.id),
        "client_id": str(invoice.client_id),
        "billing_plan_id": str(invoice.billing_plan_id) if invoice.billing_plan_id else None,
        "pricing_rule_id": str(invoice.pricing_rule_id) if invoice.pricing_rule_id else None,
        "status": invoice.status,
        "currency": invoice.currency,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "monthly_price": float(invoice.monthly_price),
        "included_tokens": invoice.included_tokens,
        "used_tokens": invoice.used_tokens,
        "overage_tokens": invoice.overage_tokens,
        "overage_price_per_1k_tokens": float(invoice.overage_price_per_1k_tokens),
        "overage_cost": float(invoice.overage_cost),
        "total_amount": float(invoice.total_amount),
        "amount": float(invoice.total_amount), # Alias for frontend
        "payment_method": invoice.payment_method,
        "payment_instructions": invoice.payment_instructions,
        "due_at": invoice.due_at.isoformat() if invoice.due_at else None,
        "due_date": invoice.due_at.isoformat() if invoice.due_at else None, # Alias for frontend
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "cancelled_at": invoice.cancelled_at.isoformat() if invoice.cancelled_at else None,
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat(),
        "payments": [serialize_payment(payment) for payment in invoice.payments],
    }


def serialize_payment(payment: CustomerPayment) -> dict:
    return {
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
