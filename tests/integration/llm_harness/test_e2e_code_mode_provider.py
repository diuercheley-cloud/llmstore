import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.reporter import Reporter
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_e2e_code_mode_provider_real_cycle(tmp_path):
    """
    Test a full cycle with a real-ish provider (mocked HTTP) to ensure
    all components (CodingLoop, Reporter, Sanitizer, Workspace) work together.
    """
    # 1. Setup workspace with a 'buggy' file
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    app_py = ws_dir / "app.py"
    app_py.write_text("def add(a, b):\n    return a - b  # Bug: should be +\n")

    test_py = ws_dir / "tests" / "test_app.py"
    test_py.parent.mkdir()
    test_py.write_text(
        "from app import add\ndef test_add():\n    assert add(2, 2) == 4\n"
    )

    # 2. Mock OpenAI-compatible response sequence
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "plan",
                                "reason": "Identify and fix addition bug",
                                "payload": {"message": "I will read app.py and fix the bug"},
                            }
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "read_file",
                                "reason": "Read app.py to see code",
                                "payload": {"path": "app.py"},
                            }
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "apply_patch",
                                "reason": "Fix addition bug",
                                "payload": {
                                    "diff": "--- app.py\n+++ app.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b  # Bug: should be +\n+    return a + b  # Fixed: using +\n"
                                },
                            }
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "run_tests",
                                "reason": "Verify fix",
                                "payload": {"test_path": "tests/test_app.py"},
                            }
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "final",
                                "reason": "Bug fixed and verified",
                                "payload": {"message": "Bug fixed successfully"},
                            }
                        )
                    }
                }
            ]
        },
    ]

    mock_transport = MagicMock(spec=httpx.AsyncBaseTransport)

    async def mock_handle_request(request):
        print(f"DEBUG: Request {request.method} {request.url}")
        if not responses:
            print("DEBUG: No more responses!")
            return httpx.Response(500, content=b"No more responses")
        resp_data = responses.pop(0)
        return httpx.Response(200, content=json.dumps(resp_data).encode())

    mock_transport.handle_async_request.side_effect = mock_handle_request

    # 3. Run CodingLoop
    async with Workspace(base_path=str(ws_dir)) as ws:
        # We need to manually set ws.path as it's usually done in CLI
        ws.path = str(ws_dir)

        with patch.dict(os.environ, {"DUMMY": "test-key"}):
            agent_client = AgentClient(
                agent_id="test-e2e", 
                provider="openai-compatible", 
                base_url="http://localhost:8080/v1/chat/completions",
                model="test-model",
                api_key_env="DUMMY",
                transport=mock_transport,
                tool_calling="json"
            )

            loop = CodingLoop(agent_client=agent_client, workspace=ws, max_steps=10)

            # 4. Mock shell execution for pytest
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

                result = await loop.run(task="Fix the bug in app.py")

                # 5. Validate results
                assert result.success is True
                assert "Bug fixed successfully" in result.message
                assert "app.py" in loop.changed_files

                # 6. Generate and validate report
                report_dir = tmp_path / "reports"
                reporter = Reporter(output_dir=str(report_dir))
                filename = reporter.generate_summary(
                    result, trace=result.trace, policy_info={"provider": "openai-compatible"}
                )
                
                # Manually call markdown generation as it's usually done in CLI
                md_content = reporter.generate_markdown_report(
                    result, 
                    blocked_actions=[], 
                    provider="openai-compatible"
                )
                md_filename = filename.replace(".json", ".md")
                md_path = report_dir / md_filename
                with open(md_path, "w") as f:
                    f.write(md_content)

                report_path = report_dir / filename
                assert report_path.exists()

                with open(report_path, "r") as f:
                    report_content = json.load(f)
                    assert report_content["success"] is True

                    run_completed_events = [
                        e for e in report_content["events"] if e["event"] == "run.completed"
                    ]
                    assert len(run_completed_events) > 0
                    run_completed_event = run_completed_events[0]
                    changed_files = run_completed_event.get("metadata", {}).get(
                        "changed_files", []
                    )
                    assert "app.py" in changed_files

                # 7. Validate markdown report
                assert md_path.exists()
                md_text = md_path.read_text()
                assert "# Agent Execution Report" in md_text
                assert "SUCCESS" in md_text
                assert "app.py" in md_text
