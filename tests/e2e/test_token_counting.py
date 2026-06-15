import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition, AgentRun
from app.models.billing.request_financial import RequestFinancial
from app.models.core.client import Client
from app.services.agents.agent_executor import AgentExecutor
from app.services.billing.pricing_engine import record_request_financials
from app.services.token_counting.token_counter import TokenCounter
from sqlalchemy import select


@pytest.mark.asyncio
async def test_token_counter_fallback_explicit(monkeypatch):
    """Ensures that fallback is marked explicitly and fallback tokenizer is used when tiktoken is unavailable."""
    settings = get_settings()
    monkeypatch.setattr(settings, "token_counting_real_enabled", True)
    monkeypatch.setattr(settings, "token_counting_fallback_allowed", True)

    with patch("importlib.import_module", side_effect=ImportError):
        tc = TokenCounter()
        res = tc.count_tokens("hello world prompt text", "completion text here", "gpt-4")
        assert res.fallback_used is True
        assert res.tokenizer_used == "fallback"
        assert res.prompt_tokens > 0
        assert res.completion_tokens > 0


@pytest.mark.asyncio
async def test_token_counter_openai_when_available(monkeypatch):
    """Ensures that openai tokenizer is used when tiktoken is available."""
    settings = get_settings()
    monkeypatch.setattr(settings, "token_counting_real_enabled", True)

    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3]  # 3 tokens
    mock_tiktoken.encoding_for_model.return_value = mock_encoding

    with patch("importlib.import_module", return_value=mock_tiktoken):
        tc = TokenCounter()
        res = tc.count_tokens("hello world", "completion", "gpt-4")
        assert res.fallback_used is False
        assert res.tokenizer_used == "openai"
        assert res.prompt_tokens == 3
        assert res.completion_tokens == 3


@pytest.mark.asyncio
async def test_budget_enforcement_uses_real_tokens(monkeypatch, session):
    """Ensures that agent run budgets use real token counting."""
    settings = get_settings()
    monkeypatch.setattr(settings, "token_counting_real_enabled", True)

    tenant_id = str(uuid.uuid4())
    client = Client(
        id=uuid.UUID(tenant_id),
        name="Token Test Client",
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=20000,
        rate_limit_per_minute=100,
        max_output_tokens=1000,
        max_context_tokens=4096,
    )
    session.add(client)

    agent_def = AgentDefinition(
        name="Budget Agent",
        version="1.0.0",
        instructions="Instructions",
        model_id="gpt-4",
        owner="tester",
        tenant_id=tenant_id,
        status="active",
        max_steps=5,
        max_runtime_seconds=300,
        agent_class="restricted_class",
    )
    session.add(agent_def)
    await session.flush()

    run = AgentRun(
        agent_id=agent_def.id,
        tenant_id=tenant_id,
        input_text="Hi",
        status="running",
        total_tokens=0,
        estimated_cost_brl=0.0,
    )
    session.add(run)
    await session.commit()

    from app.services.agents.agent_budget import AgentBudgetService

    mock_class_config = {
        "classes": {"restricted_class": {"max_tokens_per_run": 20, "max_cost_brl_per_run": 10.0}}
    }

    with patch.object(AgentBudgetService, "_config", mock_class_config):
        executor = AgentExecutor(session, run.id)

        run.total_tokens = 10
        is_valid, reason = await executor.budget_svc.validate_run_budget(agent_def, run)
        assert is_valid is True

        run.total_tokens = 25
        is_valid, reason = await executor.budget_svc.validate_run_budget(agent_def, run)
        assert is_valid is False
        assert "Token budget exceeded" in reason


@pytest.mark.asyncio
async def test_billing_records_with_real_tokens(monkeypatch, session):
    """Ensures that billing/financial records store correct token metrics."""
    settings = get_settings()
    monkeypatch.setattr(settings, "token_counting_real_enabled", True)

    client_id = uuid.uuid4()
    client = Client(id=client_id, name="Billing Test Client")
    session.add(client)
    await session.commit()

    record = await record_request_financials(
        session,
        client_id=client_id,
        endpoint_type="chat",
        provider="openai",
        model="gpt-4",
        prompt_tokens=150,
        completion_tokens=75,
        token_count_method="openai",
        tokens_estimated=False,
    )
    await session.commit()

    stmt = select(RequestFinancial).where(RequestFinancial.id == record.id)
    res = await session.execute(stmt)
    saved = res.scalar_one()

    assert saved.prompt_tokens == 150
    assert saved.completion_tokens == 75
    assert saved.total_tokens == 225
    assert saved.token_count_method == "openai"
    assert saved.tokens_estimated is False
