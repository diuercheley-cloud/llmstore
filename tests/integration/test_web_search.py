import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.agents.web_search import (
    AgentWebSearchCache,
    AgentWebSearchPolicyEvent,
    AgentWebSearchQuery,
)
from app.services.agents.tools.web_search_tool import WebSearchToolAdapter
from sqlalchemy import select

print("METADATA TABLES DECLARED IN PYTHON:", list(Base.metadata.tables.keys()))


@pytest_asyncio.fixture
async def test_search_env_setup(admin_client, monkeypatch):
    # Enable Web Search flags by default
    monkeypatch.setenv("AGENT_WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED", "true")
    monkeypatch.setenv("AGENT_WEB_SEARCH_ALLOWLIST_ENABLED", "true")

    # Clear setting cache
    get_settings.cache_clear()
    get_settings()

    from app.db.session import get_db_session
    db_session_override = app.dependency_overrides[get_db_session]

    async for db in db_session_override():
        plan = BillingPlan(
            id=uuid.uuid4(),
            code="search_plan",
            name="Search Plan",
            rate_limit_per_minute=100,
            daily_token_quota=100000,
            weekly_token_quota=500000,
            monthly_token_quota=1000000,
            max_output_tokens=1024,
        )
        db.add(plan)
        await db.commit()

        client_a = Client(
            id=uuid.uuid4(),
            name="tenant-a",
            billing_status="active",
            billing_plan_id=plan.id,
            is_blocked=False,
        )
        db.add(client_a)
        await db.commit()

        prefix_a = "sk-tenant-a1"
        key_a = ApiKey(
            client_id=client_a.id,
            name="key_a",
            key_prefix=prefix_a,
            key_hash="hash_a",
            is_active=True,
        )
        db.add(key_a)
        await db.commit()

        yield {
            "client": admin_client,
            "db": db,
            "client_a": client_a,
            "headers_a": {"Authorization": f"Bearer {prefix_a}.val"},
        }

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_web_search_disabled_bloqueia(test_search_env_setup, monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_ENABLED", "false")
    get_settings.cache_clear()

    setup = test_search_env_setup
    db = setup["db"]

    adapter = WebSearchToolAdapter()
    with pytest.raises(Exception) as exc:
        await adapter.execute(
            query="test query",
            tenant_id=str(setup["client_a"].id),
            provider="mock",
            db=db,
        )
    assert "capability is disabled" in str(exc.value.detail)

    # Verify a policy event was logged
    stmt = select(AgentWebSearchPolicyEvent).where(
        AgentWebSearchPolicyEvent.event_type == "disabled"
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    assert event is not None
    assert event.tenant_id == str(setup["client_a"].id)


@pytest.mark.asyncio
async def test_external_network_disabled_bloqueia_provider_real(
    test_search_env_setup, monkeypatch
):
    monkeypatch.setenv("AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED", "false")
    get_settings.cache_clear()

    setup = test_search_env_setup
    db = setup["db"]
    adapter = WebSearchToolAdapter()
    with pytest.raises(Exception) as exc:
        await adapter.execute(
            query="weather tomorrow",
            tenant_id=str(setup["client_a"].id),
            provider="http",
            db=db,
        )
    assert "External network is disabled" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_mock_provider_retorna_mock_true(test_search_env_setup):
    setup = test_search_env_setup
    db = setup["db"]

    adapter = WebSearchToolAdapter()
    result = await adapter.execute(
        query="LLM stack",
        tenant_id=str(setup["client_a"].id),
        provider="mock",
        db=db,
    )

    assert "query_hash" in result
    assert len(result["results"]) > 0
    assert result["results"][0]["provider"] == "mock"
    assert "github.com" in result["citation"]
    assert "audit_event_id" in result
    assert len(result["result_ids"]) == len(result["results"])

    # Verify audit query created
    stmt = select(AgentWebSearchQuery).where(
        AgentWebSearchQuery.query_hash == result["query_hash"]
    )
    res = await db.execute(stmt)
    query_record = res.scalar_one_or_none()
    assert query_record is not None
    assert query_record.tenant_id == str(setup["client_a"].id)


@pytest.mark.asyncio
async def test_allowlist_bloqueia_dominio_nao_permitido(
    test_search_env_setup, monkeypatch
):
    monkeypatch.setenv("AGENT_WEB_SEARCH_ALLOWLIST_ENABLED", "true")
    get_settings.cache_clear()

    setup = test_search_env_setup
    db = setup["db"]
    adapter = WebSearchToolAdapter()

    # The query "test query" normally generates urls like https://search-results.local/result-1 (allowed)
    # Let's mock provider results return a blocked domain
    with patch(
        "app.services.agents.web_search.mock_search_provider.MockSearchProvider.search",
        return_value=[
            {
                "title": "Banned Result",
                "snippet": "Contains info.",
                "url": "https://unallowed-domain.com/page",
                "provider": "mock",
                "confidence": 0.9,
            }
        ],
    ):
        result = await adapter.execute(
            query="test query",
            tenant_id=str(setup["client_a"].id),
            provider="mock",
            db=db,
        )
        # BannedResult domain should be filtered out, leaving results empty
        assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_cache_hit_miss_funciona(test_search_env_setup):
    setup = test_search_env_setup
    db = setup["db"]

    adapter = WebSearchToolAdapter()
    q = "unique test query cache"

    # Clean cache first
    await db.execute(select(AgentWebSearchCache))

    # 1. Miss
    res_miss = await adapter.execute(
        query=q,
        tenant_id=str(setup["client_a"].id),
        provider="mock",
        db=db,
    )
    # Check cache table
    stmt = select(AgentWebSearchCache).where(
        AgentWebSearchCache.query_hash == res_miss["query_hash"]
    )
    res = await db.execute(stmt)
    cache_entry = res.scalar_one_or_none()
    assert cache_entry is not None

    # 2. Hit
    res_hit = await adapter.execute(
        query=q,
        tenant_id=str(setup["client_a"].id),
        provider="mock",
        db=db,
    )
    assert res_hit["query_hash"] == res_miss["query_hash"]
    # Audit log should log provider as "cache:mock"
    stmt_audit = select(AgentWebSearchQuery).where(
        AgentWebSearchQuery.id == uuid.UUID(res_hit["audit_event_id"])
    )
    res_audit = await db.execute(stmt_audit)
    audit_rec = res_audit.scalar_one_or_none()
    assert audit_rec is not None
    assert audit_rec.provider == "cache:mock"


@pytest.mark.asyncio
async def test_prompt_injection_sanitized(test_search_env_setup):
    setup = test_search_env_setup
    db = setup["db"]

    adapter = WebSearchToolAdapter()

    # Query with prompt injection keywords triggers MockSearchProvider to return one
    result = await adapter.execute(
        query="prompt injection test",
        tenant_id=str(setup["client_a"].id),
        provider="mock",
        db=db,
    )

    assert len(result["results"]) > 0
    res_item = result["results"][0]
    assert "[Redacted: Prompt Injection Attempt]" in res_item["title"]
    assert "[Content redacted by safety engine to prevent prompt injection]" in res_item["snippet"]

    # Verify event was logged
    stmt = select(AgentWebSearchPolicyEvent).where(
        AgentWebSearchPolicyEvent.event_type == "prompt_injection_sanitized"
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    assert event is not None
    assert event.tenant_id == str(setup["client_a"].id)


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_web_search_admin_endpoints(mock_verify, test_search_env_setup, admin_token_headers):
    setup = test_search_env_setup
    client = setup["client"]

    # 1. Test POST /admin/agents/tools/web-search/test
    response = await client.post(
        "/admin/agents/tools/web-search/test",
        headers=admin_token_headers,
        json={"query": "LLM stacks", "provider": "mock"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "query_hash" in res_data
    assert len(res_data["results"]) > 0

    # 2. Test GET /admin/agents/web-search/audit
    response_audit = await client.get(
        "/admin/agents/web-search/audit",
        headers=admin_token_headers
    )
    assert response_audit.status_code == 200
    audit_data = response_audit.json()
    assert len(audit_data) > 0
    assert audit_data[0]["query"] == "LLM stacks"

    # 3. Test GET /admin/agents/web-search/cache
    response_cache = await client.get(
        "/admin/agents/web-search/cache",
        headers=admin_token_headers
    )
    assert response_cache.status_code == 200
    cache_data = response_cache.json()
    assert len(cache_data) > 0
