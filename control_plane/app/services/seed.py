import logging
import os

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.models.api_key import ApiKey
from app.models.client import Client
from app.services.admin_rbac import ensure_admin_rbac_seed
from app.services.agents.tool_adapter_seeding import seed_tool_adapters
from app.services.billing import ensure_default_billing_plans, ensure_default_pricing_rules
from app.services.chaos_engineering import ChaosEngineeringService
from app.services.compliance_readiness import ComplianceReadinessService
from app.services.model_registry import ensure_default_model
from app.services.multi_cluster_operations import MultiClusterOperationsService
from app.services.routing.commercial_safety_policies import ensure_default_safety_policies
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def seed_defaults(session: AsyncSession) -> None:
    settings = get_settings()
    await ensure_admin_rbac_seed(session)
    await ensure_default_model(session)
    if settings.agent_tool_adapters_enabled or settings.agent_runtime_enabled:
        await seed_tool_adapters(session)
    plans = await ensure_default_billing_plans(session)
    await ensure_default_pricing_rules(session, plans)
    if getattr(settings, "commercial_guardrails_enabled", False):
        await ensure_default_safety_policies(session)

    # --- Feature Seeding ---

    # Chaos Seeding
    if os.getenv("CHAOS_ENABLED", "false").lower() == "true":
        chaos_svc = ChaosEngineeringService(session)
        await chaos_svc.seed_default_experiments()
        logger.info("Seeded default chaos experiments.")

    # Compliance Seeding
    if (
        os.getenv("COMPLIANCE_ENABLED", "false").lower() == "true"
        or os.getenv("COMPLIANCE_READINESS_ENABLED", "false").lower() == "true"
    ):
        comp_svc = ComplianceReadinessService(session)
        await comp_svc.seed_frameworks()
        logger.info("Seeded default compliance frameworks.")

    # Multi-cluster Seeding
    if settings.multi_cluster_enabled:
        mc_svc = MultiClusterOperationsService(session)
        clusters = await mc_svc.list_clusters()
        if not clusters:
            await mc_svc.create_cluster(
                name="Cluster São Paulo (Default)",
                cluster_type="remote",
                base_url="https://sp-demo.kleber.ai",
                location="sa-east-1"
            )
            logger.info("Seeded default cluster for multi-cluster management.")

    # --- Demo Client ---
    demo_plan = plans["basic"]

    result = await session.execute(select(Client).where(Client.name == settings.demo_client_name))
    client = result.scalar_one_or_none()
    if client is None:
        client = Client(
            name=settings.demo_client_name,
            description="Demo client seeded for local validation",
            billing_status="active",
            rate_limit_per_minute=settings.demo_rate_limit_per_minute,
            daily_token_quota=settings.demo_daily_token_quota,
            monthly_token_quota=settings.demo_monthly_token_quota,
            max_context_tokens=settings.max_context_tokens,
            max_output_tokens=settings.max_completion_tokens,
            billing_plan_id=demo_plan.id,
        )
        session.add(client)
        await session.flush()
    else:
        client.description = "Demo client seeded for local validation"
        client.billing_status = "active"
        client.rate_limit_per_minute = settings.demo_rate_limit_per_minute
        client.daily_token_quota = settings.demo_daily_token_quota
        client.monthly_token_quota = settings.demo_monthly_token_quota
        client.max_context_tokens = settings.max_context_tokens
        client.max_output_tokens = settings.max_completion_tokens
        client.billing_plan_id=demo_plan.id

    key_result = await session.execute(select(ApiKey).where(ApiKey.client_id == client.id, ApiKey.name == "demo-default"))
    existing_key = key_result.scalar_one_or_none()
    if existing_key is None:
        plaintext = generate_api_key()
        api_key = ApiKey(
            client_id=client.id,
            name="demo-default",
            key_prefix=short_prefix(plaintext),
            key_hash=hash_secret(plaintext),
        )
        session.add(api_key)
        logger.warning(
            "demo api key generated for seeded client; plaintext is intentionally not logged",
            extra={"extra_data": {"demo_client": client.name, "key_prefix": short_prefix(plaintext)}},
        )
