import pytest
import uuid
from fastapi import HTTPException
from app.services.queue_manager import QueueManager, QueueOverloaded, QueueTimeout
from app.services.backend_slot_manager import BackendSlotManager
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_queue_mapping():
    slot_manager = MagicMock(spec=BackendSlotManager)
    qm = QueueManager(slot_manager)
    
    assert qm._resolve_queue_name("free") == "inference_free"
    assert qm._resolve_queue_name("basic") == "inference_basic"
    assert qm._resolve_queue_name("pro") == "inference_premium"
    assert qm._resolve_queue_name("enterprise") == "inference_premium"
    assert qm._resolve_queue_name("any", is_admin=True) == "inference_admin"

@pytest.mark.asyncio
async def test_queue_overloaded():
    slot_manager = MagicMock(spec=BackendSlotManager)
    # Backend always busy, so requests stay in waiting
    slot_manager.try_acquire = AsyncMock(return_value=False)
    qm = QueueManager(slot_manager)
    
    limit = qm.queues["inference_free"]["max_waiting"]
    backend_id = uuid.uuid4()
    
    tasks = []
    for _ in range(limit):
        # We need to use a real context manager call or simulate it
        ctx = qm.slot(plan_code="free", backend_id=backend_id)
        tasks.append(asyncio.create_task(ctx.__aenter__()))
    
    # Wait until all tasks have entered the queue
    for _ in range(200):
        if qm.waiting_counts["inference_free"] == limit:
            break
        await asyncio.sleep(0.005)
    
    # Next one should fail immediately because max_waiting is reached
    with pytest.raises(QueueOverloaded) as exc:
        async with qm.slot(plan_code="free", backend_id=backend_id):
            pass
    assert exc.value.queue_name == "inference_free"
    
    # Cleanup
    for t in tasks:
        t.cancel()

@pytest.mark.asyncio
async def test_queue_timeout():
    slot_manager = MagicMock(spec=BackendSlotManager)
    slot_manager.try_acquire = AsyncMock(return_value=False) # Backends never available
    qm = QueueManager(slot_manager)
    
    # Set a very short timeout for testing
    qm.queues["inference_free"]["timeout"] = 0.2
    backend_id = uuid.uuid4()
    
    with pytest.raises(QueueTimeout) as exc:
        async with qm.slot(plan_code="free", backend_id=backend_id):
            pass
    assert exc.value.queue_name == "inference_free"
