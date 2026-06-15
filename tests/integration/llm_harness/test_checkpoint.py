from unittest.mock import MagicMock

from scripts.llm_harness.checkpoint import CheckpointManager
from scripts.llm_harness.coding_loop import CodingLoop


def test_checkpoint_manager(tmp_path):
    cm = CheckpointManager(checkpoint_dir=str(tmp_path))
    state = {"step": 1, "history": []}
    cm.save_checkpoint("run1", state)

    loaded = cm.load_checkpoint("run1")
    assert loaded == state
    assert cm.load_checkpoint("run2") is None


def test_coding_loop_state_save_load():
    agent_client = MagicMock()
    workspace = MagicMock()
    loop = CodingLoop(agent_client, workspace)

    loop.history = [{"role": "user", "content": "hi"}]
    loop.total_tokens = 100

    state = loop.get_state()
    assert state["total_tokens"] == 100

    new_loop = CodingLoop(agent_client, workspace)
    new_loop.load_state(state)
    assert new_loop.history == loop.history
    assert new_loop.total_tokens == 100
