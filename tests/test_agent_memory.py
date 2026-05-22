import pytest
import uuid
from app.services.agents.agent_memory import AgentMemoryService, MemoryDisabledError, SecretFoundError
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents import agent_state
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_memory_tenant_isolation(session):
    # Setup
    agent_id = uuid.uuid4()
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    
    # Enable memory for test
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    
    # Create policies
    policy_service = MemoryPolicyService(session)
    await policy_service.create_policy({"tenant_id": tenant_a, "memory_type": "short_term"})
    await policy_service.create_policy({"tenant_id": tenant_b, "memory_type": "short_term"})
    
    service = AgentMemoryService(session)
    
    # Tenant A writes
    await service.write_memory(tenant_a, agent_id, "short_term", "Private data for A")
    
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
        await service.write_memory("t1", uuid.uuid4(), "short_term", "test")

@pytest.mark.asyncio
async def test_secret_blocking(session):
    settings = get_settings()
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    
    service = AgentMemoryService(session)
    with pytest.raises(SecretFoundError):
        await service.write_memory("t1", uuid.uuid4(), "short_term", "my secret api_key is sk-12345")

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
    item = await service.write_memory(tenant_id, agent_id, "short_term", "test")
    
    # Check access events
    from app.models.agents import AgentMemoryAccessEvent
    from sqlalchemy.future import select
    res = await session.execute(select(AgentMemoryAccessEvent).where(AgentMemoryAccessEvent.memory_item_id == item.id))
    events = res.scalars().all()
    
    assert len(events) == 1
    assert events[0].operation == "write"
    
    # Read and check again
    await service.read_memory(tenant_id, agent_id)
    res = await session.execute(select(AgentMemoryAccessEvent).where(AgentMemoryAccessEvent.memory_item_id == item.id, AgentMemoryAccessEvent.operation == "read"))
    assert res.scalar_one_or_none() is not None
