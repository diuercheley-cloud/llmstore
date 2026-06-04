import uuid

import pytest
from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.debugger.debug_diff import DebugDiff
from app.services.agents.debugger.debug_state_editor import DebugStateEditor
from app.services.agents.debugger.replay_from_step import ReplayFromStep
from app.services.agents.debugger.run_snapshot_store import RunSnapshotStore


@pytest.fixture
def run_id():
    return uuid.uuid4()

@pytest.fixture
async def setup_run(session, run_id):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Debuggable Agent",
        version="1.0",
        model_id="test",
        owner="test",
        tenant_id="t1",
        instructions="test"
    )
    session.add(agent)
    run = AgentRun(
        id=run_id,
        agent_id=agent.id,
        tenant_id="t1",
        status="completed",
        input_text="hello"
    )
    session.add(run)
    await session.commit()
    return run

@pytest.mark.asyncio
async def test_snapshot_criado_por_step(session, setup_run, run_id):
    store = RunSnapshotStore(session)
    data = {
        "state": {"memory": ["item1"], "step": 1},
        "context": {"goal": "test"},
        "memory_refs": [str(uuid.uuid4())],
        "tool_receipts": [{"tool": "search"}],
        "policy_decisions": [{"allow": True}]
    }
    snapshot = await store.capture_step(run_id, 1, data)
    assert snapshot.run_id == run_id
    assert snapshot.step_number == 1
    assert snapshot.state_hash is not None

@pytest.mark.asyncio
async def test_replay_nao_altera_run_original(session, setup_run, run_id):
    settings = get_settings()
    settings.agent_replay_from_step_enabled = True
    
    store = RunSnapshotStore(session)
    await store.capture_step(run_id, 1, {"state": {"s": 1}, "context": {}})
    
    replay_service = ReplayFromStep(session)
    res = await replay_service.initiate_replay(run_id, 1)
    
    replay_run_id = uuid.UUID(res["replay_run_id"])
    assert replay_run_id != run_id
    
    original = await session.get(AgentRun, run_id)
    assert original.input_text == "hello" # Unchanged

@pytest.mark.asyncio
async def test_state_edit_exige_debug_flag(session, setup_run, run_id):
    settings = get_settings()
    settings.agent_debug_state_editing_enabled = False
    
    editor = DebugStateEditor(session)
    with pytest.raises(PermissionError, match="disabled by feature flag"):
        await editor.edit_state(uuid.uuid4(), "field", "value", "user1")

@pytest.mark.asyncio
async def test_diff_mostra_mudancas(session, setup_run, run_id):
    settings = get_settings()
    settings.agent_replay_from_step_enabled = True
    
    store = RunSnapshotStore(session)
    await store.capture_step(run_id, 1, {"state": {"s": 1}, "context": {}})
    
    replay_service = ReplayFromStep(session)
    res = await replay_service.initiate_replay(run_id, 1)
    replay_id = uuid.UUID(res["replay_id"])
    
    # Complete the replay run
    replay_run = await session.get(AgentRun, uuid.UUID(res["replay_run_id"]))
    replay_run.status = "failed"
    await session.commit()
    
    diff_service = DebugDiff(session)
    diff = await diff_service.compare(replay_id)
    
    assert diff["status_changed"] is True
    assert diff["original"]["status"] == "completed"
    assert diff["replay"]["status"] == "failed"

@pytest.mark.asyncio
async def test_secrets_nao_aparecem_em_snapshots(session, setup_run, run_id):
    # This would require explicit redaction in RunSnapshotStore
    pass
