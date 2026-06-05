import hashlib
import json
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.core.time import utc_now
from app.services.agents.memory.advanced_memory_service import AdvancedMemoryService
from app.models.advanced_memory import MemoryEvent, MemoryEventType, MemoryScope


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_memory_event_hash_chain(mock_session):
    service = AdvancedMemoryService(mock_session)
    
    agent_id = uuid.uuid4()
    tenant_id = "test-tenant"
    
    # Mocking first event creation (no previous event)
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result1
    
    event1 = await service.append_event(
        tenant_id=tenant_id,
        agent_id=agent_id,
        scope=MemoryScope.SHORT_TERM,
        event_type=MemoryEventType.CREATED,
        payload={"msg": "first"}
    )
    
    assert event1.previous_event_hash is None
    assert event1.logical_counter == 1
    
    # Mocking second event creation (with previous event)
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = event1
    mock_session.execute.return_value = mock_result2
    
    event2 = await service.append_event(
        tenant_id=tenant_id,
        agent_id=agent_id,
        scope=MemoryScope.SHORT_TERM,
        event_type=MemoryEventType.CREATED,
        payload={"msg": "second"}
    )
    
    assert event2.previous_event_hash == event1.event_hash
    assert event2.logical_counter == 2
    assert event2.event_hash != event1.event_hash


@pytest.mark.asyncio
async def test_forgetting_curve_logic(mock_session):
    service = AdvancedMemoryService(mock_session)
    agent_id = uuid.uuid4()
    
    now = utc_now()
    # Create mock events with different importance and access counts
    e1 = MagicMock(spec=MemoryEvent)
    e1.importance_score = 1.0
    e1.access_count = 0
    e1.created_at = now - timedelta(hours=10)
    e1.last_accessed_at = None
    
    e2 = MagicMock(spec=MemoryEvent)
    e2.importance_score = 1.0
    e2.access_count = 5
    e2.created_at = now - timedelta(hours=10)
    e2.last_accessed_at = now # Just accessed
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [e1, e2]
    mock_session.execute.return_value = mock_result
    
    await service.compute_forgetting_scores(agent_id)
    
    # e2 should have a higher decay_score (more memorable) because it was recently accessed and has more frequency
    assert e2.decay_score > e1.decay_score


@pytest.mark.asyncio
async def test_memory_redaction(mock_session):
    service = AdvancedMemoryService(mock_session)
    
    event = MagicMock(spec=MemoryEvent)
    event.id = uuid.uuid4()
    event.tenant_id = "t1"
    event.agent_id = uuid.uuid4()
    event.scope = MemoryScope.SHORT_TERM
    event.event_type = MemoryEventType.CREATED
    event.payload = {"secret": "1234"}
    event.logical_counter = 1
    event.event_hash = "hash1"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = event
    mock_session.execute.return_value = mock_result
    
    await service.redact_memory(event.id, "GDPR request")
    
    assert event.payload["status"] == "redacted"
    assert "GDPR" in event.payload["reason"]


@pytest.mark.asyncio
async def test_memory_tenant_isolation(mock_session):
    service = AdvancedMemoryService(mock_session)
    agent_id = uuid.uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    event = await service.append_event(
        tenant_id="tenant-A",
        agent_id=agent_id,
        scope=MemoryScope.SHORT_TERM,
        event_type=MemoryEventType.CREATED,
        payload={"data": "private"}
    )
    
    assert event.tenant_id == "tenant-A"


@pytest.mark.asyncio
async def test_memory_forgetting(mock_session):
    service = AdvancedMemoryService(mock_session)
    
    event = MagicMock(spec=MemoryEvent)
    event.id = uuid.uuid4()
    event.tenant_id = "t1"
    event.agent_id = uuid.uuid4()
    event.scope = MemoryScope.SHORT_TERM
    event.event_type = MemoryEventType.CREATED
    event.importance_score = 1.0
    event.logical_counter = 1
    event.event_hash = "hash1"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = event
    mock_session.execute.return_value = mock_result
    
    await service.forget_memory(event.id)
    
    assert event.importance_score == 0.0
    assert event.decay_score == 0.0
