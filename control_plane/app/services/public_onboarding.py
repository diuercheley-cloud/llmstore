import hashlib
import json
import re

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.models.billing.billing_plan import BillingPlan
from app.models.billing.pricing_rule import PricingRule
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.schemas.public import PublicSignupRequest
from app.services.billing import resolve_effective_plan
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

settings = get_settings()

PUBLIC_PLAN_FEATURES = {
    "free": [
        "No credit card required",
        "Basic shared capacity",
        "Community-grade response times",
    ],
    "basic": [
        "Streaming enabled",
        "Production API key",
        "Email support",
    ],
    "pro": [
        "Higher throughput",
        "Priority queueing",
        "Launch support for production",
    ],
    "enterprise": [
        "Dedicated rollout planning",
        "Custom quotas and routing",
        "Priority support channel",
    ],
    "unlimited": [
        "Unlimited token usage",
        "Zero token overage charges",
        "Premier production support",
    ],
}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "tenant"


def build_account_name(company: str | None, email: str) -> str:
    del company
    base = slugify(email.split("@", 1)[0])
    suffix = hashlib.sha1(email.strip().lower().encode("utf-8")).hexdigest()[:8]
    return f"{base[:48]}-{suffix}"


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise HTTPException(status_code=422, detail="invalid email")
    return value


def marketing_summary(plan: BillingPlan, _pricing_rule: PricingRule | None) -> dict:
    effective = resolve_effective_plan(
        Client(
            name="preview",
            rate_limit_per_minute=plan.rate_limit_per_minute,
            daily_token_quota=plan.daily_token_quota,
            monthly_token_quota=plan.monthly_token_quota,
            max_context_tokens=settings.max_context_tokens,
            max_output_tokens=plan.max_output_tokens,
            billing_plan=plan,
        )
    )
    return {
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "monthly_price": float(effective.monthly_price),
        "currency": effective.currency,
        "rate_limit_per_minute": effective.rate_limit_per_minute,
        "daily_token_quota": effective.daily_token_quota,
        "monthly_token_quota": effective.monthly_token_quota,
        "max_output_tokens": effective.max_output_tokens,
        "max_context_tokens": effective.max_context_tokens,
        "requests_per_day": effective.requests_per_day,
        "allow_streaming": effective.allow_streaming,
        "rag_enabled": effective.rag_enabled,
        "tts_enabled": effective.tts_enabled,
        "embeddings_enabled": effective.embeddings_enabled,
        "responses_enabled": effective.responses_enabled,
        "export_enabled": effective.export_enabled,
        "support_level": effective.support_level,
        "overage_price_per_1k_tokens": float(effective.overage_price_per_1k_tokens),
        "features": PUBLIC_PLAN_FEATURES.get(plan.code, []),
        "highlight": plan.code == "pro",
    }


async def list_public_plans(session: AsyncSession) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(BillingPlan)
                .options(selectinload(BillingPlan.pricing_rules))
                .where(BillingPlan.is_active.is_(True))
                .order_by(BillingPlan.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    serialized = []
    for plan in rows:
        pricing_rule = next((item for item in plan.pricing_rules if item.is_active), None)
        serialized.append(marketing_summary(plan, pricing_rule))
    return serialized


async def create_public_signup(
    session: AsyncSession,
    payload: PublicSignupRequest,
) -> tuple[Client, BillingPlan, ApiKey, str]:
    email = normalize_email(payload.email)
    account_name = build_account_name(payload.company, email)
    existing = await session.execute(select(Client).where(Client.name == account_name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="account already exists for this email")

    plan = (
        await session.execute(
            select(BillingPlan)
            .options(selectinload(BillingPlan.pricing_rules))
            .where(BillingPlan.code == payload.plan_code, BillingPlan.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")

    metadata = {
        "signup_source": "public_web",
        "full_name": payload.full_name.strip(),
        "email": email,
        "company": (payload.company or "").strip() or None,
        "use_case": (payload.use_case or "").strip() or None,
    }
    client = Client(
        name=account_name,
        description=(payload.company or payload.full_name).strip(),
        billing_status="active",
        billing_plan_id=plan.id,
        rate_limit_per_minute=plan.rate_limit_per_minute,
        daily_token_quota=plan.daily_token_quota,
        monthly_token_quota=plan.monthly_token_quota,
        max_context_tokens=settings.max_context_tokens,
        max_output_tokens=plan.max_output_tokens,
        metadata_json=json.dumps(metadata),
    )
    session.add(client)
    await session.flush()

    plaintext = generate_api_key()
    api_key = ApiKey(
        client_id=client.id,
        name="default",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(["inference:chat", "portal:read"]),
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(client)
    await session.refresh(api_key)
    return client, plan, api_key, plaintext
