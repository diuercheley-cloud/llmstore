import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import AgentPolicyDecision
from app.services.agents.agent_memory import (
    AgentMemoryService,
    ConsentRequiredError,
    MemoryDisabledError,
    SecretFoundError,
)
from app.services.agents.agent_policy_engine import AgentPolicyEngine
from app.services.agents.memory_consent import MemoryConsentService
from app.services.agents.memory_indexing import (
    cosine_similarity,
    get_mock_embedding,
)
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents.memory_retention import MemoryRetentionService


@pytest.fixture(autouse=True)
def mock_agent_policy_engine():
    async def mock_evaluate_action_v2(self, request):
        return AgentPolicyDecision(
            run_id=request.run_id,
            action_type=request.action_type,
            subject=request.subject,
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            risk_level="low",
            result="allow",
            reason="Mock allow for memory tests",
            policy_version="1.1.0",
            created_at=utc_now(),
        )

    with patch.object(AgentPolicyEngine, "evaluate_action_v2", mock_evaluate_action_v2):
        yield


@pytest.mark.asyncio
async def test_memory_tenant_isolation(session):
    # Setup
    agent_id = uuid.uuid4()
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    user_a = "user-a"

    # Enable memory for test
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True

    # Create policies
    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_a, "memory_type": "short_term"})
    await policy_service.create_policy({"tenant_id": tenant_b, "memory_type": "short_term"})

    service = AgentMemoryService(session)

    # Tenant A writes
    await service.write_memory(
        tenant_a, agent_id, "short_term", "Private data for A", user_id=user_a
    )

    # Tenant B should NOT see A's data
    items_b = await service.read_memory(tenant_b, agent_id)
    assert len(items_b) == 0

    # Tenant A should see its data
    items_a = await service.read_memory(tenant_a, agent_id)
    assert len(items_a) == 1
    assert items_a[0].raw_content == "Private data for A"


@pytest.mark.asyncio
async def test_memory_disabled_blocks_write(session):
    settings = get_settings()
    settings.agent_memory_enabled = False

    service = AgentMemoryService(session)
    with pytest.raises(MemoryDisabledError):
        await service.write_memory("t1", uuid.uuid4(), "short_term", "test", user_id="u1")


@pytest.mark.asyncio
async def test_secret_blocking(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    service = AgentMemoryService(session)
    with pytest.raises(SecretFoundError):
        await service.write_memory(
            "t1", uuid.uuid4(), "short_term", "my secret api_key is sk-12345", user_id="u1"
        )


@pytest.mark.asyncio
async def test_access_event_logging(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    tenant_id = "t1"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    item = await service.write_memory(tenant_id, agent_id, "short_term", "test", user_id="u1")

    # Check access events
    from app.models.agents.agents import AgentMemoryAccessEvent
    from sqlalchemy.future import select

    res = await session.execute(
        select(AgentMemoryAccessEvent).where(AgentMemoryAccessEvent.memory_item_id == item.id)
    )
    events = res.scalars().all()

    assert len(events) == 1
    assert events[0].operation == "write"

    # Read and check again
    await service.read_memory(tenant_id, agent_id)
    res = await session.execute(
        select(AgentMemoryAccessEvent).where(
            AgentMemoryAccessEvent.memory_item_id == item.id,
            AgentMemoryAccessEvent.operation == "read",
        )
    )
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_write_sem_consentimento_falha(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_consent_required = True

    tenant_id = "t_consent"
    agent_id = uuid.uuid4()
    user_id = "u_noconsent"

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})

    service = AgentMemoryService(session)
    with pytest.raises(ConsentRequiredError):
        await service.write_memory(tenant_id, agent_id, "long_term", "hello", user_id=user_id)

    # Grant consent
    consent_service = MemoryConsentService(session)
    await consent_service.create_consent(tenant_id, user_id, "long_term", agent_id)

    # Should work now
    item = await service.write_memory(tenant_id, agent_id, "long_term", "hello", user_id=user_id)
    assert item is not None


@pytest.mark.asyncio
async def test_write_sem_retention_policy_falha(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    service = AgentMemoryService(session)
    with pytest.raises(ValueError, match="No retention policy found"):
        await service.write_memory("t_nopolicy", uuid.uuid4(), "short_term", "data", user_id="u1")


@pytest.mark.asyncio
async def test_ttl_expira_memoria(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    tenant_id = "t_ttl"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy(
        {"tenant_id": tenant_id, "memory_type": "short_term", "retention_days": 0}
    )

    service = AgentMemoryService(session)
    item = await service.write_memory(tenant_id, agent_id, "short_term", "data", user_id="u1")

    # Manually backdate retention_until
    item.retention_until = utc_now() - timedelta(days=1)
    await session.commit()

    # Run retention
    retention_service = MemoryRetentionService(session)
    res = await retention_service.run_retention()
    assert res["items_deleted"] == 1

    items = await service.read_memory(tenant_id, agent_id)
    assert len(items) == 0


@pytest.mark.asyncio
async def test_redaction_bloqueia_secret(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    tenant_id = "t_redact"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy(
        {"tenant_id": tenant_id, "memory_type": "short_term", "redaction_enabled": True}
    )

    service = AgentMemoryService(session)
    item = await service.write_memory(
        tenant_id, agent_id, "short_term", "my email is test@email@.com and pii-123", user_id="u1"
    )

    assert "[REDACTED]@" in item.raw_content
    assert "[REDACTED]-123" in item.raw_content
    assert item.redaction_status == "completed"


@pytest.mark.asyncio
async def test_delete_request_remove(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True

    tenant_id = "t_del"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    await service.write_memory(tenant_id, agent_id, "short_term", "data1", user_id="u1")
    await service.write_memory(tenant_id, agent_id, "short_term", "data2", user_id="u1")

    retention_service = MemoryRetentionService(session)
    await retention_service.create_delete_request(tenant_id, agent_id)

    res = await retention_service.process_delete_requests()
    assert res["requests_processed"] == 1
    assert res["items_deleted"] == 2

    items = await service.read_memory(tenant_id, agent_id)
    assert len(items) == 0


@pytest.mark.asyncio
async def test_export_nao_contem_secrets(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_export_enabled = True

    tenant_id = "t_exp"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    item = await service.write_memory(tenant_id, agent_id, "short_term", "data1", user_id="u1")

    # Manually inject secret into DB to simulate failure of initial redaction or drift
    item.raw_content = "some sk-123 key"
    await session.commit()

    exports = await service.export_memory(tenant_id)
    # The export should skip items containing secrets dynamically
    assert len(exports) == 0


@pytest.mark.asyncio
async def test_search_disabled_falha(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_search_enabled = False

    service = AgentMemoryService(session)
    with pytest.raises(MemoryDisabledError, match="Memory search is disabled"):
        await service.search_memory("t1", uuid.uuid4(), "query")


@pytest.mark.asyncio
async def test_indexing_nao_mistura_tenants(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_search_enabled = True

    tenant_a = "t_idx_a"
    tenant_b = "t_idx_b"
    agent_id_a = uuid.uuid4()
    agent_id_b = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_a, "memory_type": "short_term"})
    await policy_service.create_policy({"tenant_id": tenant_b, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    await service.write_memory(tenant_a, agent_id_a, "short_term", "special keyword", user_id="u1")
    await service.write_memory(tenant_b, agent_id_b, "short_term", "special keyword", user_id="u2")

    res_a = await service.search_memory(tenant_a, agent_id_a, "special")
    assert len(res_a) == 1
    assert res_a[0].tenant_id == tenant_a

    # Should not see tenant A data when searching with tenant B
    res_b = await service.search_memory(tenant_b, agent_id_b, "special")
    assert len(res_b) == 1
    assert res_b[0].tenant_id == tenant_b


@pytest.mark.asyncio
async def test_semantic_search_returns_relevant_memory(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_search_enabled = True
    settings.agent_memory_semantic_search_enabled = True

    tenant_id = "t_semantic"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    await service.write_memory(
        tenant_id, agent_id, "short_term", "O gato subiu na árvore", user_id="u1"
    )
    await service.write_memory(
        tenant_id, agent_id, "short_term", "O cachorro correu no parque", user_id="u2"
    )

    results = await service.search_memory(tenant_id, agent_id, "gato")
    assert len(results) >= 1
    contents = [r.raw_content for r in results]
    assert any("gato" in c for c in contents)


@pytest.mark.asyncio
async def test_like_fallback_works_in_mock(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_search_enabled = True
    settings.agent_memory_semantic_search_enabled = False

    tenant_id = "t_like"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    await service.write_memory(tenant_id, agent_id, "short_term", "banana amarela", user_id="u1")
    await service.write_memory(tenant_id, agent_id, "short_term", "morango vermelho", user_id="u2")

    results = await service.search_memory(tenant_id, agent_id, "banana")
    assert len(results) == 1
    assert results[0].raw_content == "banana amarela"


@pytest.mark.asyncio
async def test_context_injection_builds_block(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_context_injection_enabled = True

    tenant_id = "t_ctx"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "short_term"})

    from app.services.agents.memory_consent import MemoryConsentService

    consent_service = MemoryConsentService(session)
    await consent_service.create_consent(tenant_id, "u1", "long_term", agent_id)

    service = AgentMemoryService(session)
    await service.write_memory(
        tenant_id,
        agent_id,
        "long_term",
        "O cliente prefere e-mails resumidos.",
        user_id="u1",
        summary="Preference: concise emails",
    )

    ctx = await service.build_memory_context(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query="e-mails resumidos",
        user_id="u1",
        memory_type="long_term",
    )

    assert "Relevant Memory" in ctx["context_block"]
    assert len(ctx["memory_ids"]) > 0
    assert ctx["total_tokens"] > 0


@pytest.mark.asyncio
async def test_context_token_limit_is_respected(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_context_injection_enabled = True

    tenant_id = "t_tokenlim"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})

    from app.services.agents.memory_consent import MemoryConsentService

    consent_service = MemoryConsentService(session)
    await consent_service.create_consent(tenant_id, "u1", "long_term", agent_id)
    await consent_service.create_consent(tenant_id, "u2", "long_term", agent_id)

    service = AgentMemoryService(session)
    await service.write_memory(
        tenant_id, agent_id, "long_term", "A" * 5000, user_id="u1", summary="Long memory 1"
    )
    await service.write_memory(
        tenant_id, agent_id, "long_term", "B" * 5000, user_id="u2", summary="Long memory 2"
    )

    ctx = await service.build_memory_context(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query="memory",
        user_id="u1",
        memory_type="long_term",
        max_tokens=100,
    )

    assert ctx["total_tokens"] <= 120  # allow small padding
    if ctx["memory_ids"]:
        assert ctx["total_tokens"] <= 120


@pytest.mark.asyncio
async def test_secret_like_memory_not_reinjected(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_context_injection_enabled = True

    tenant_id = "t_secret"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})

    service = AgentMemoryService(session)
    # This will fail to write due to secret detection, so we write directly
    from datetime import timedelta

    from app.models.agents.agents import AgentMemoryItem

    item = AgentMemoryItem(
        tenant_id=tenant_id,
        agent_id=agent_id,
        memory_type="long_term",
        content_hash="abc",
        raw_content="minha chave api sk-12345",
        summary="Secret key",
        retention_until=utc_now() + timedelta(days=30),
    )
    session.add(item)
    await session.commit()

    ctx = await service.build_memory_context(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query="chave api",
        user_id="u1",
        memory_type="long_term",
    )

    assert len(ctx["memory_ids"]) == 0
    assert ctx["context_block"] == ""


@pytest.mark.asyncio
async def test_tenant_isolation_semantic_search(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_memory_search_enabled = True
    settings.agent_memory_semantic_search_enabled = True

    tenant_a = "t_iso_a"
    tenant_b = "t_iso_b"
    agent_id_a = uuid.uuid4()
    agent_id_b = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_a, "memory_type": "short_term"})
    await policy_service.create_policy({"tenant_id": tenant_b, "memory_type": "short_term"})

    service = AgentMemoryService(session)
    await service.write_memory(
        tenant_a, agent_id_a, "short_term", "dado confidencial do tenant A", user_id="u1"
    )
    await service.write_memory(
        tenant_b, agent_id_b, "short_term", "dado confidencial do tenant B", user_id="u2"
    )

    semantic_results_a = await service.semantic_search_memory(tenant_a, agent_id_a, "confidencial")
    semantic_results_b = await service.semantic_search_memory(tenant_b, agent_id_b, "confidencial")

    for r in semantic_results_a:
        assert r["memory_id"] not in [s["memory_id"] for s in semantic_results_b]

    ids_a = {r["memory_id"] for r in semantic_results_a}
    ids_b = {r["memory_id"] for r in semantic_results_b}
    assert ids_a.isdisjoint(ids_b)


@pytest.mark.asyncio
async def test_memory_ids_appear_in_step_metadata(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_context_injection_enabled = True

    tenant_id = "t_stepmeta"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})

    from app.services.agents.memory_consent import MemoryConsentService

    consent_service = MemoryConsentService(session)
    await consent_service.create_consent(tenant_id, "u1", "long_term", agent_id)

    service = AgentMemoryService(session)
    item = await service.write_memory(
        tenant_id,
        agent_id,
        "long_term",
        "memória importante para o agente",
        user_id="u1",
        summary="Important context",
    )

    ctx = await service.build_memory_context(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query="importante",
        user_id="u1",
        memory_type="long_term",
    )

    assert len(ctx["memory_ids"]) >= 1
    assert str(item.id) in ctx["memory_ids"]


@pytest.mark.asyncio
async def test_cosine_similarity_basic():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)

    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)

    d = [0.5, 0.5, 0.0]
    val = cosine_similarity(a, d)
    assert 0.5 < val < 1.0


@pytest.mark.asyncio
async def test_mock_embedding_deterministic():
    emb1 = get_mock_embedding("hello world")
    emb2 = get_mock_embedding("hello world")
    assert emb1 == emb2
    assert len(emb1) == 384

    emb3 = get_mock_embedding("different text")
    assert emb1 != emb3


@pytest.mark.asyncio
async def test_context_injection_disabled_by_default(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_long_term_memory_enabled = True
    settings.agent_memory_context_injection_enabled = False
    settings.agent_memory_consent_required = False

    tenant_id = "t_disabled"
    agent_id = uuid.uuid4()

    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_id, "memory_type": "long_term"})

    service = AgentMemoryService(session)
    ctx = await service.build_memory_context(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query="test",
        user_id="u1",
    )

    assert ctx["context_block"] == ""
    assert ctx["memory_ids"] == []
    assert ctx["total_tokens"] == 0
