import json
import os
from unittest.mock import patch

import pytest

from scripts.llm_harness.cli import main


@pytest.fixture
def scenarios_file(tmp_path):
    scenarios = [
        {"name": "task1", "task": "fix bug 1", "agent_id": "agent1"},
        {"name": "task2", "task": "fix bug 2", "agent_id": "agent2"}
    ]
    f = tmp_path / "scenarios.json"
    f.write_text(json.dumps(scenarios))
    return str(f)

def test_cli_code_batch_stub_fail(scenarios_file):
    with patch("sys.argv", ["cli.py", "code-batch", "--file", scenarios_file]):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1 

def test_cli_code_batch_allow_stub(scenarios_file, tmp_path):
    with patch("sys.argv", ["cli.py", "code-batch", "--file", scenarios_file, "--allow-stub-code-agent", "--concurrency", "2"]):
        with patch.dict(os.environ, {}, clear=True):
            cwd = os.getcwd()
            try:
                os.chdir(str(tmp_path))
                main()
                # Verify reports exist
                reports = os.listdir("artifacts/llm_harness")
                json_reports = [r for r in reports if r.startswith("batch_report_") and r.endswith(".json")]
                md_reports = [r for r in reports if r.startswith("batch_report_") and r.endswith(".md")]
                assert len(json_reports) > 0
                assert len(md_reports) > 0
            finally:
                os.chdir(cwd)

@pytest.mark.asyncio
async def test_batch_workspace_isolation_verified():
    # Keep this existing test to preserve low-level workspace isolation coverage.
    from scripts.llm_harness.workspace import Workspace
    async with Workspace() as ws1:
        ws1.write_file("a.txt", "1")
        async with Workspace() as ws2:
            ws2.write_file("a.txt", "2")
            assert ws1.read_file("a.txt") == "1"
            assert ws2.read_file("a.txt") == "2"
