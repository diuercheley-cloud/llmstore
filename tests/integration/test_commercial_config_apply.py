import pytest
from app.models.commercial.commercial_routing_config import CommercialRoutingConfig
from app.models.core.admin_action_log import AdminActionLog
from app.schemas.routing import TaskType
from app.services.routing.commercial_config_store import CommercialConfigStore
from app.services.routing.commercial_ranker import rank_commercial_routes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_commercial_config_specificity_precedence(session: AsyncSession):
    store = CommercialConfigStore(session)

    # 1. Global config
    await store.apply_config(scope_type="global", cost_multiplier=1.1)

    # 2. Provider config
    await store.apply_config(scope_type="provider", provider="openai", cost_multiplier=1.2)

    # 3. Model config
    await store.apply_config(scope_type="model", model="gpt-4", cost_multiplier=1.3)

    # 4. Provider-Model config
    await store.apply_config(
        scope_type="provider_model", provider="openai", model="gpt-4", cost_multiplier=1.4
    )

    # Test precedence
    # provider_model
    conf = await store.get_effective_config(provider="openai", model="gpt-4")
    assert conf["cost_multiplier"] == 1.4

    # model (different provider)
    conf = await store.get_effective_config(provider="other", model="gpt-4")
    assert conf["cost_multiplier"] == 1.3

    # provider (different model)
    conf = await store.get_effective_config(provider="openai", model="other")
    assert conf["cost_multiplier"] == 1.2

    # global (different provider and model)
    conf = await store.get_effective_config(provider="other", model="other")
    assert conf["cost_multiplier"] == 1.1


@pytest.mark.asyncio
async def test_commercial_config_safety_validation(session: AsyncSession):
    store = CommercialConfigStore(session)

    # Cost multiplier out of bounds
    with pytest.raises(ValueError, match="out of safe bounds"):
        await store.apply_config(scope_type="global", cost_multiplier=5.0)

    # Weights sum != 1.0
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        await store.apply_config(
            scope_type="global", margin_weight=0.5, latency_weight=0.1, quality_weight=0.1
        )

    # Force override
    config = await store.apply_config(scope_type="global", cost_multiplier=5.0, force=True)
    assert config.cost_multiplier == 5.0


@pytest.mark.asyncio
async def test_commercial_config_deactivate_and_rollback(session: AsyncSession):
    store = CommercialConfigStore(session)

    c1 = await store.apply_config(scope_type="global", cost_multiplier=1.1)
    c2 = await store.apply_config(scope_type="global", cost_multiplier=1.2)

    # c2 should be active, c1 inactive
    assert c2.is_active is True

    res = await session.execute(
        select(CommercialRoutingConfig).where(CommercialRoutingConfig.id == c1.id)
    )
    c1_db = res.scalar_one()
    assert c1_db.is_active is False

    # Rollback to c1
    rolled = await store.rollback_config(scope_type="global", provider=None, model=None)
    assert rolled.id == c1.id
    assert rolled.is_active is True

    res = await session.execute(
        select(CommercialRoutingConfig).where(CommercialRoutingConfig.id == c2.id)
    )
    c2_db = res.scalar_one()
    assert c2_db.is_active is False


@pytest.mark.asyncio
async def test_ranker_uses_dynamic_config(session: AsyncSession):
    store = CommercialConfigStore(session)
    await store.apply_config(scope_type="provider", provider="local", cost_multiplier=2.0)

    dynamic_configs = await store.list_configs(active_only=True)

    candidates = [{"provider": "local", "model": "local-model"}]
    ranked, _, _ = rank_commercial_routes(
        candidates=candidates,
        client_plan="pro",
        task_type=TaskType.general,
        estimated_input_tokens=1000,
        estimated_output_tokens=1000,
        dynamic_configs=dynamic_configs,
    )

    assert len(ranked) == 1
    cost_with_dynamic = ranked[0].estimated_cost_brl

    ranked_no_dynamic, _, _ = rank_commercial_routes(
        candidates=candidates,
        client_plan="pro",
        task_type=TaskType.general,
        estimated_input_tokens=1000,
        estimated_output_tokens=1000,
        dynamic_configs=None,
    )
    cost_no_dynamic = ranked_no_dynamic[0].estimated_cost_brl

    assert cost_with_dynamic == pytest.approx(cost_no_dynamic * 2.0)


@pytest.mark.asyncio
async def test_commercial_config_audit_logging(session: AsyncSession):
    store = CommercialConfigStore(session)
    config = await store.apply_config(
        scope_type="global", cost_multiplier=1.1, created_by="admin@test.com", notes="test audit"
    )

    # In AdminActionLog, target_id is not a column, we use payload_json
    res = await session.execute(
        select(AdminActionLog).where(AdminActionLog.action == "apply_commercial_config")
    )
    audit = res.scalars().all()[-1]  # Get last one
    assert audit.action == "apply_commercial_config"
    assert audit.payload_json["cost_multiplier"] == 1.1
