import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.llm_harness.coding_loop import CodingLoop


@pytest.mark.asyncio
async def test_parallel_read_file():
    agent_client = MagicMock()
    workspace = MagicMock()
    workspace.path = "/tmp/test"

    loop = CodingLoop(agent_client, workspace)

    # Mock read_file to be slow
    async def slow_read(p):
        await asyncio.sleep(0.1)
        return f"content of {p}"

    loop.read_file = AsyncMock(side_effect=slow_read)

    actions = [
        {"action_type": "read_file", "path": "file1.py"},
        {"action_type": "read_file", "path": "file2.py"},
        {"action_type": "read_file", "path": "file3.py"},
    ]

    parallel_action = {"action_type": "parallel", "actions": actions}

    start = asyncio.get_event_loop().time()
    results = await loop._execute_single_action(parallel_action)
    duration = asyncio.get_event_loop().time() - start

    assert len(results) == 3
    assert results == ["content of file1.py", "content of file2.py", "content of file3.py"]
    # With max_parallel=2, it should take ~0.2s (file1, file2 in parallel, then file3)
    assert 0.15 < duration < 0.25


@pytest.mark.asyncio
async def test_parallel_side_effect_rejection():
    agent_client = MagicMock()
    workspace = MagicMock()

    loop = CodingLoop(agent_client, workspace)

    actions = [
        {"action_type": "read_file", "path": "file1.py"},
        {"action_type": "apply_patch", "diff": "some diff"},
    ]

    parallel_action = {"action_type": "parallel", "actions": actions}

    with pytest.raises(ValueError, match="is not allowed in parallel mode"):
        await loop._execute_single_action(parallel_action)
