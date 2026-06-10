import asyncio
import hashlib
import hmac
import json
import os
import uuid
import zoneinfo
from datetime import UTC, datetime
from pathlib import Path

# Force SQLite for tests and enable feature flags before app import
TEST_DB_FILE = Path("/tmp/test-event-driven.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["AGENT_EVENT_DRIVEN_ENABLED"] = "true"
os.environ["AGENT_EVENT_HOOKS_ENABLED"] = "true"
os.environ["AGENT_CRON_TRIGGERS_ENABLED"] = "true"
os.environ["AGENT_PUBSUB_TRIGGERS_ENABLED"] = "true"
os.environ["AGENT_EXTERNAL_WEBHOOK_TRIGGERS_ENABLED"] = "true"
os.environ["AGENT_ASYNC_EXECUTION_ENABLED"] = "true"
os.environ["AGENT_EXECUTION_PLANE_ENABLED"] = "true"
os.environ["AGENT_RUNTIME_ENABLED"] = "true"

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db, get_db_session
from app.main import app as main_app
from app.models.agents.agent_events import (
    AgentEventDedupKey,
    AgentEventDelivery,
    AgentEventSource,
    AgentEventTrigger,
    AgentScheduledTrigger,
    AgentWebhookTrigger,
)
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.events.cron_triggers import calculate_next_run
from app.services.agents.events.event_deduplication import is_duplicate, sanitize_payload
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def override_get_db():
    async with SessionLocal() as session:
        yield session

main_app.dependency_overrides[get_db] = override_get_db
main_app.dependency_overrides[get_db_session] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Force settings needed for testing
    settings = get_settings()
    orig_event_driven = settings.agent_event_driven_enabled
    orig_event_hooks = settings.agent_event_hooks_enabled
    orig_cron_triggers = settings.agent_cron_triggers_enabled
    orig_pubsub_triggers = settings.agent_pubsub_triggers_enabled
    orig_webhook_triggers = settings.agent_external_webhook_triggers_enabled
    
    orig_runtime = settings.agent_runtime_enabled
    orig_plane = settings.agent_execution_plane_enabled
    orig_async = settings.agent_async_execution_enabled
    
    settings.agent_event_driven_enabled = True
    settings.agent_event_hooks_enabled = True
    settings.agent_cron_triggers_enabled = True
    settings.agent_pubsub_triggers_enabled = True
    settings.agent_external_webhook_triggers_enabled = True
    
    settings.agent_runtime_enabled = True
    settings.agent_execution_plane_enabled = True
    settings.agent_async_execution_enabled = True  # Avoid executing actual LLM steps
    
    from app.models.agents.agent_events import (
        AgentEventDelivery,
        AgentEventSubscription,
        AgentWebhookTrigger,
    )
    from app.models.agents.agent_execution import (
        AgentExecutionDeadLetter,
        AgentExecutionJob,
        AgentExecutionLease,
        AgentExecutionRetry,
        AgentWorkerHeartbeat,
    )
    from app.models.agents.agents import (
        AgentDefinition,
        AgentPolicyDecision,
        AgentRun,
        AgentRunEvent,
        AgentRunStep,
    )
    from app.models.core.client import Client
    tables = [
        Client.__table__,
        AgentDefinition.__table__,
        AgentRun.__table__,
        AgentRunEvent.__table__,
        AgentRunStep.__table__,
        AgentPolicyDecision.__table__,
        AgentExecutionJob.__table__,
        AgentWorkerHeartbeat.__table__,
        AgentExecutionLease.__table__,
        AgentExecutionRetry.__table__,
        AgentExecutionDeadLetter.__table__,
        AgentEventSource.__table__,
        AgentEventTrigger.__table__,
        AgentEventDelivery.__table__,
        AgentScheduledTrigger.__table__,
        AgentWebhookTrigger.__table__,
        AgentEventDedupKey.__table__,
        AgentEventSubscription.__table__
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
    yield
    
    settings.agent_event_driven_enabled = orig_event_driven
    settings.agent_event_hooks_enabled = orig_event_hooks
    settings.agent_cron_triggers_enabled = orig_cron_triggers
    settings.agent_pubsub_triggers_enabled = orig_pubsub_triggers
    settings.agent_external_webhook_triggers_enabled = orig_webhook_triggers
    
    settings.agent_runtime_enabled = orig_runtime
    settings.agent_execution_plane_enabled = orig_plane
    settings.agent_async_execution_enabled = orig_async
    
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=tables))

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": "test-admin-token"}

@pytest_asyncio.fixture
async def setup_agent():
    async with SessionLocal() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(),
            name="Test Event Agent",
            tenant_id="test-tenant",
            status="active",
            instructions="Handle events",
            model_id="mock-model",
            owner="admin",
            version="1.0.0"
        )
        db.add(agent)
        await db.commit()
        return agent.id

async def wait_for_delivery(delivery_id: uuid.UUID, timeout: float = 2.0) -> AgentEventDelivery:
    start_time = datetime.now(UTC)
    while (datetime.now(UTC) - start_time).total_seconds() < timeout:
        async with SessionLocal() as db:
            stmt = select(AgentEventDelivery).where(AgentEventDelivery.id == delivery_id)
            res = await db.execute(stmt)
            delivery = res.scalar_one_or_none()
            if delivery and delivery.status in ["delivered", "failed"]:
                return delivery
        await asyncio.sleep(0.1)
    raise TimeoutError("Background execution task timed out")


@pytest.mark.asyncio
async def test_feature_flags_guard_endpoints(async_client, admin_headers, setup_agent):
    settings = get_settings()
    settings.agent_event_driven_enabled = False
    
    # 1. Admin creation is rejected
    res = await async_client.post(
        "/admin/agents/event-sources",
        json={"type": "webhook", "config": {}, "tenant_id": "test-tenant"},
        headers=admin_headers
    )
    assert res.status_code == 403
    
    # 2. Public webhook is rejected
    res = await async_client.post(
        f"/agents/events/webhooks/{uuid.uuid4()}",
        json={"foo": "bar"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_webhook_trigger_creation_and_delivery(async_client, admin_headers, setup_agent):
    agent_id = setup_agent
    
    # 1. Create webhook trigger (which automatically sets up signature / webhook trigger metadata)
    trigger_payload = {
        "agent_id": str(agent_id),
        "trigger_type": "on_webhook",
        "config": {
            "secret": "my-webhook-secret",
            "signature_header": "X-Custom-Sig"
        },
        "tenant_id": "test-tenant"
    }
    
    res = await async_client.post("/admin/agents/event-triggers", json=trigger_payload, headers=admin_headers)
    assert res.status_code == 200
    trigger_data = res.json()
    trigger_id = trigger_data["id"]
    
    # Verify associated WebhookTrigger entry was created
    async with SessionLocal() as db:
        stmt = select(AgentWebhookTrigger).where(AgentWebhookTrigger.trigger_id == uuid.UUID(trigger_id))
        res_db = await db.execute(stmt)
        webhook_trigger = res_db.scalar_one()
        assert webhook_trigger.secret_hash == "my-webhook-secret"
        assert webhook_trigger.signature_header == "X-Custom-Sig"
        
    # 2. Test webhook signature validation: invalid signature rejected
    res = await async_client.post(
        f"/agents/events/webhooks/{trigger_id}",
        json={"input_text": "run agent"},
        headers={"X-Custom-Sig": "invalid-sig"}
    )
    assert res.status_code == 403
    
    # 3. Test webhook signature validation: valid signature accepted
    payload = {"input_text": "hello proactive world"}
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    valid_sig = hmac.new(b"my-webhook-secret", body, hashlib.sha256).hexdigest()
    
    res = await async_client.post(
        f"/agents/events/webhooks/{trigger_id}",
        json=payload,
        headers={"X-Custom-Sig": valid_sig}
    )
    assert res.status_code == 200
    
    # 4. Wait for background task to execute AgentRun
    delivery_res = await async_client.get(f"/admin/agents/event-deliveries?trigger_id={trigger_id}", headers=admin_headers)
    assert delivery_res.status_code == 200
    deliveries = delivery_res.json()
    assert len(deliveries) > 0
    delivery_id = uuid.UUID(deliveries[0]["id"])
    
    delivery = await wait_for_delivery(delivery_id)
    assert delivery.status == "delivered"
    assert delivery.agent_run_id is not None
    
    # Check that AgentRun was created in DB
    async with SessionLocal() as db:
        stmt = select(AgentRun).where(AgentRun.id == delivery.agent_run_id)
        res_db = await db.execute(stmt)
        run = res_db.scalar_one()
        assert run.input_text == "hello proactive world"
        assert run.correlation_id == str(delivery_id)


@pytest.mark.asyncio
async def test_event_deduplication(setup_agent):
    async with SessionLocal() as db:
        event_payload = {"some_data": 123}
        dedup_key = "event-id-100"
        
        # First call is NOT a duplicate
        is_dup1 = await is_duplicate(db, dedup_key)
        assert is_dup1 is False
        
        # Second call with same key IS a duplicate
        is_dup2 = await is_duplicate(db, dedup_key)
        assert is_dup2 is True


@pytest.mark.asyncio
async def test_event_payload_secrets_redaction(setup_agent):
    payload = {
        "user": "kleber",
        "api_key": "sk-123456",
        "nested": {
            "password": "my-secret-pass",
            "normal_field": "hello"
        }
    }
    
    sanitized = sanitize_payload(payload)
    assert sanitized["user"] == "kleber"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "hello"


@pytest.mark.asyncio
async def test_rate_limiting_and_paused_triggers(async_client, admin_headers, setup_agent):
    agent_id = setup_agent
    
    # 1. Create a trigger with a rate limit of 1 event per hour
    trigger_payload = {
        "agent_id": str(agent_id),
        "trigger_type": "on_webhook",
        "config": {
            "secret": "secret",
            "signature_header": "X-Agent-Signature"
        },
        "rate_limit": 1,
        "tenant_id": "test-tenant"
    }
    res = await async_client.post("/admin/agents/event-triggers", json=trigger_payload, headers=admin_headers)
    assert res.status_code == 200
    trigger_id = res.json()["id"]
    
    # Prepare webhook firing payload
    payload = {"input_text": "rate limit test"}
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    
    # Fire first webhook: Accepted
    res1 = await async_client.post(f"/agents/events/webhooks/{trigger_id}", json=payload, headers={"X-Agent-Signature": sig})
    assert res1.status_code == 200
    
    # Fire second webhook: Fails rate limit check (policy check returns False, not processed)
    # The endpoint calls process_webhook which fails, returning 403 or rejecting because check_policy returns False.
    res2 = await async_client.post(f"/agents/events/webhooks/{trigger_id}", json=payload, headers={"X-Agent-Signature": sig})
    assert res2.status_code == 403
    
    # 2. Test Paused triggers: pause trigger and verify firing returns 403/failed
    res_pause = await async_client.post(f"/admin/agents/event-triggers/{trigger_id}/pause", headers=admin_headers)
    assert res_pause.status_code == 200
    
    res_paused_fire = await async_client.post(f"/agents/events/webhooks/{trigger_id}", json=payload, headers={"X-Agent-Signature": sig})
    assert res_paused_fire.status_code == 403


@pytest.mark.asyncio
async def test_cron_timezone_next_run():
    # Cron schedule for every day at 14:00 inside America/Sao_Paulo (which is UTC-3 or UTC-2 depending on DST)
    cron_expr = "0 14 * * *"
    timezone_str = "America/Sao_Paulo"
    
    start_time = datetime(2026, 5, 27, 10, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
    # Next occurrence of 14:00 Sao Paulo time on May 27th is 14:00 Sao Paulo, which is 17:00 UTC
    next_run = calculate_next_run(cron_expr, start_time, timezone_str)
    
    assert next_run.hour == 17
    assert next_run.minute == 0
    assert next_run.tzinfo == zoneinfo.ZoneInfo("UTC")
