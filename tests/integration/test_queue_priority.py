import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.queue_manager import QueueManager


@pytest.mark.asyncio
async def test_priority_jumping():
    slot_manager = MagicMock()
    # Initially no slots available for first 2 calls (polling)
    # Then slots become available.
    # We want to ensure that even if 'free' started polling first,
    # 'admin' gets it as soon as a slot is available because of priority.
    
    # We use a stateful mock to simulate backend slot becoming available
    slot_available = False
    
    async def mocked_try_acquire(backend_id):
        return slot_available

    slot_manager.try_acquire = AsyncMock(side_effect=mocked_try_acquire)
    slot_manager.release = AsyncMock()
    qm = QueueManager(slot_manager)
    
    # Set limits for easy testing
    for q in qm.queues:
        qm.queues[q]["max_active"] = 1
        qm.queues[q]["timeout"] = 2.0

    results = []
    backend_id = uuid.uuid4()
    
    async def run_task(name, plan, is_admin=False):
        try:
            async with qm.slot(plan_code=plan, is_admin=is_admin, backend_id=backend_id):
                results.append(name)
        except Exception as e:
            results.append(f"error_{name}_{type(e).__name__}")

    # 1. Start a Free request that will wait
    t1 = asyncio.create_task(run_task("free", "free"))
    for _ in range(100):
        if qm.waiting_counts["inference_free"] == 1:
            break
        await asyncio.sleep(0.005)
    
    # 2. Start an Admin request that will also wait
    t2 = asyncio.create_task(run_task("admin", "any", is_admin=True))
    for _ in range(100):
        if qm.waiting_counts["inference_admin"] == 1:
            break
        await asyncio.sleep(0.005)
    
    # Now make slot available
    slot_available = True
    
    # Both should eventually finish. 
    # Due to priority, Admin should see the available slot first or be allowed to take it first.
    await asyncio.gather(t1, t2)
    
    # The order of results should be admin then free
    assert results == ["admin", "free"]

@pytest.mark.asyncio
async def test_starvation_prevention_by_timeout():
    # If Admin constantly takes slots, Free might timeout. 
    # This is expected behavior for strict priority.
    slot_manager = MagicMock()
    slot_manager.try_acquire = AsyncMock(return_value=True) # Always available
    qm = QueueManager(slot_manager)
    
    # Force free to wait by filling its active slot
    # Free max_active = 1
    qm.queues["inference_free"]["max_active"] = 1
    qm.queues["inference_free"]["timeout"] = 0.5
    
    async with qm.slot(plan_code="free"):
        # While one is active, try another one
        with pytest.raises(Exception): # QueueTimeout or QueueOverloaded depending on max_waiting
            async with qm.slot(plan_code="free"):
                pass
