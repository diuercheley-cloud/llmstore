import pytest
import uuid
from app.services.agents.digital_twins.twin_registry import TwinRegistry
from app.services.agents.digital_twins.twin_service import DigitalTwinService
from app.services.agents.digital_twins.twin_state import TwinState
from app.models.digital_twin import DigitalTwin, DigitalTwinCommand, DigitalTwinSafetyEvent
from app.core.config import get_settings

@pytest.fixture
def twin_id():
    return uuid.uuid4()

@pytest.fixture
async def setup_twin(session, twin_id):
    registry = TwinRegistry(session)
    twin = await registry.register("t1", {
        "name": "Industrial Pump 1",
        "twin_type": "actuator",
        "connector_type": "mock"
    })
    # Set ID to our fixture ID
    twin.id = twin_id
    await session.commit()
    return twin

@pytest.mark.asyncio
async def test_read_state_funciona_em_mock(session, setup_twin, twin_id):
    settings = get_settings()
    settings.agent_digital_twins_enabled = True
    
    # Pre-populate state
    state_service = TwinState(session)
    await state_service.update_state(twin_id, {"pressure": 120, "rpm": 1500})
    
    service = DigitalTwinService(session)
    state = await service.read_twin(twin_id)
    assert state["pressure"] == 120

@pytest.mark.asyncio
async def test_command_bloqueado_por_default(session, setup_twin, twin_id):
    settings = get_settings()
    settings.agent_digital_twins_enabled = True
    settings.agent_physical_actuation_enabled = False # Disabled by default
    
    service = DigitalTwinService(session)
    with pytest.raises(PermissionError, match="Physical actuation is globally disabled"):
        await service.send_command(twin_id, "start", {})

@pytest.mark.asyncio
async def test_actuation_exige_approval(session, setup_twin, twin_id):
    settings = get_settings()
    settings.agent_digital_twins_enabled = True
    settings.agent_physical_actuation_enabled = True
    
    service = DigitalTwinService(session)
    res = await service.send_command(twin_id, "increase_pressure", {"inc": 10})
    
    assert res["status"] == "pending_approval"
    assert "command_id" in res

@pytest.mark.asyncio
async def test_safety_interlock_bloqueia_comando_perigoso(session, setup_twin, twin_id):
    settings = get_settings()
    settings.agent_digital_twins_enabled = True
    settings.agent_physical_actuation_enabled = True
    
    service = DigitalTwinService(session)
    # Attempt high voltage command
    res = await service.send_command(twin_id, "set_voltage_high", {})
    
    assert res["status"] == "blocked_by_safety"
    assert "Interlock tripped" in res["reason"]
    
    # Check if safety event was recorded
    from sqlalchemy.future import select
    stmt = select(DigitalTwinSafetyEvent).where(DigitalTwinSafetyEvent.twin_id == twin_id)
    events = list((await session.execute(stmt)).scalars().all())
    assert len(events) == 1
    assert events[0].event_type == "interlock_trip"
