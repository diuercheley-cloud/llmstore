from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.auto_mode import AutoModeApprovalProvider, AutoModeRunner
from scripts.llm_harness.cli_commands import run_fix_error_command, run_terminal_command
from scripts.llm_harness.coding_loop import CodingLoop, ExecutionResult
from scripts.llm_harness.workspace import Workspace


@pytest.fixture
def mock_coding_loop(tmp_path):
    ws = Workspace(base_path=str(tmp_path))
    # We mock client
    client = MagicMock()
    loop = CodingLoop(
        agent_client=client,
        workspace=ws,
        timeout=10,
        use_docker=False,
    )
    return loop


def test_auto_mode_limits_fixes(mock_coding_loop):
    _ = AutoModeRunner(
        coding_loop=mock_coding_loop,
        max_auto_fixes=2,
        stop_on_risk=False,
        require_approval_for_edits=False,
    )

    provider = mock_coding_loop.approval_provider
    assert isinstance(provider, AutoModeApprovalProvider)

    # First edit action -> allowed
    action = {"action_type": "write_file", "path": "app.py", "content": "print('ok')"}
    allowed, _ = provider.request_approval(action)
    assert allowed is True
    assert provider.edit_count == 1

    # Second edit action -> allowed
    allowed, _ = provider.request_approval(action)
    assert allowed is True
    assert provider.edit_count == 2

    # Third edit action -> denied (exceeds max_auto_fixes = 2)
    allowed, _ = provider.request_approval(action)
    assert allowed is False
    assert provider.edit_count == 3


def test_auto_mode_stop_on_risk(mock_coding_loop):
    _ = AutoModeRunner(
        coding_loop=mock_coding_loop,
        max_auto_fixes=3,
        stop_on_risk=True,
        require_approval_for_edits=False,
    )

    provider = mock_coding_loop.approval_provider

    action = {"action_type": "write_file", "path": "app.py"}
    policy_decision_ok = {"allowed": True}
    policy_decision_blocked = {"allowed": False, "reason": "blocked by policy"}

    # Allowed by policy -> allowed by approval provider
    allowed, _ = provider.request_approval(action, policy_decision=policy_decision_ok)
    assert allowed is True

    # Blocked by policy -> denied by approval provider (due to stop_on_risk=True)
    allowed, _ = provider.request_approval(action, policy_decision=policy_decision_blocked)
    assert allowed is False


@patch("builtins.input", return_value="y")
def test_auto_mode_require_approval_for_edits(mock_input, mock_coding_loop):
    _ = AutoModeRunner(
        coding_loop=mock_coding_loop,
        max_auto_fixes=3,
        stop_on_risk=False,
        require_approval_for_edits=True,
    )

    provider = mock_coding_loop.approval_provider

    # Read action (not an edit) -> auto approved without requesting input
    action_read = {"action_type": "read_file", "path": "app.py"}
    allowed, _ = provider.request_approval(action_read)
    assert allowed is True
    assert mock_input.call_count == 0

    # Edit action -> requires interactive approval
    # Mocking TTY behavior to avoid interactive requirement errors
    with patch("sys.stdin.isatty", return_value=True):
        action_edit = {"action_type": "write_file", "path": "app.py", "content": "1"}
        allowed, _ = provider.request_approval(action_edit)
        assert allowed is True
        assert mock_input.call_count == 1


@pytest.mark.asyncio
async def test_auto_mode_retries_with_diagnostics(mock_coding_loop):
    failing = ExecutionResult(
        success=False,
        error='Traceback (most recent call last):\n  File "app.py", line 4, in <module>\nValueError: bad input',
        events=[],
    )
    succeeding = ExecutionResult(success=True, message="fixed", events=[])
    mock_coding_loop.run = AsyncMock(side_effect=[failing, succeeding])

    runner = AutoModeRunner(
        coding_loop=mock_coding_loop,
        max_auto_fixes=2,
        stop_on_risk=False,
        require_approval_for_edits=False,
    )

    result = await runner.run_task("Fix the bug")

    assert result.success is True
    assert result.metrics["auto_mode_retries_used"] == 1
    assert mock_coding_loop.run.await_count == 2
    retried_task = mock_coding_loop.run.await_args_list[1].args[0]
    assert "Auto Mode retry attempt 2" in retried_task
    assert "ValueError: bad input" in retried_task


@pytest.mark.asyncio
async def test_auto_mode_stops_on_policy_risk(mock_coding_loop):
    blocked = ExecutionResult(
        success=False,
        error="command blocked",
        events=[{"event": "policy.blocked", "message": "denied"}],
    )
    mock_coding_loop.run = AsyncMock(return_value=blocked)

    runner = AutoModeRunner(
        coding_loop=mock_coding_loop,
        max_auto_fixes=3,
        stop_on_risk=True,
        require_approval_for_edits=False,
    )

    result = await runner.run_task("Fix the bug")

    assert result.success is False
    assert result.metrics["auto_mode_stopped_on_risk"] is True
    assert mock_coding_loop.run.await_count == 1


@pytest.mark.asyncio
@patch("scripts.llm_harness.legacy_runner.run_harness", new_callable=AsyncMock)
async def test_fix_error_dry_run(mock_run_harness, tmp_path):
    # Setup temporary error log file
    log_file = tmp_path / "error.log"
    log_file.write_text("test.py:10: error: ZeroDivisionError: division by zero")

    args = Namespace(
        command="fix-error",
        from_file=str(log_file),
        run_command=None,
        dry_run=True,
        workspace=str(tmp_path),
        config=None,
        agent_id=None,
        provider="stub",
        model=None,
        base_url=None,
        sandbox=None,
        docker_image=None,
        self_heal=None,
        api_key_env=None,
        timeout=None,
        local_model_timeout=None,
        auto_increase_timeout=None,
        max_retries=None,
        stream=None,
        stream_local_default=None,
        verbose_stream=None,
        tool_calling=None,
        supports_tool_calling=None,
        workspace_mount_path=None,
        temp_base_dir=None,
        sandbox_network=None,
        proxy_url=None,
        loop_timeout=None,
        max_output_chars=None,
        report_output_path=None,
        cache=None,
        no_cache=False,
        cache_dir=None,
        pricing_file=None,
        max_cost_per_run=None,
        max_tokens_per_run=None,
        memory=None,
        memory_dir=None,
        memory_retention_days=None,
        agent_mode=None,
        approval_mode=None,
        approval_default=None,
        edit_action_before_run=None,
        checkpoint_dir=None,
        checkpoint_every_step=None,
        multimodal=None,
        max_tokens=None,
        auto=None,
        max_auto_fixes=None,
        stop_on_risk=None,
        require_approval_for_edits=None,
        allow_stub_code_agent=True,
        allow_test_short_circuit=False,
    )

    mock_run_harness.return_value = ExecutionResult(success=True, message="Fixed!")

    with patch("builtins.print") as mock_print:
        await run_fix_error_command(args)
        # Check dry run printed info
        any_dry_run = any("Dry run mode active" in call[0][0] for call in mock_print.call_args_list)
        assert any_dry_run
        mock_run_harness.assert_called_once()


@pytest.mark.asyncio
async def test_terminal_diagnose_from_stderr_file(tmp_path):
    stderr_file = tmp_path / "stderr.log"
    stderr_file.write_text('Traceback (most recent call last):\n  File "app.py", line 3, in <module>\nValueError: bad input\n')

    args = Namespace(
        command="terminal",
        terminal_command="diagnose",
        stderr_file=str(stderr_file),
        last_command=None,
        workspace=str(tmp_path),
        config=None,
        agent_id=None,
        provider="stub",
        model=None,
        base_url=None,
        sandbox=None,
        docker_image=None,
        self_heal=None,
        api_key_env=None,
        timeout=None,
        local_model_timeout=None,
        auto_increase_timeout=None,
        max_retries=None,
        stream=None,
        stream_local_default=None,
        verbose_stream=None,
        tool_calling=None,
        supports_tool_calling=None,
        workspace_mount_path=None,
        temp_base_dir=None,
        sandbox_network=None,
        proxy_url=None,
        loop_timeout=None,
        max_output_chars=None,
        report_output_path=None,
        cache=None,
        no_cache=False,
        cache_dir=None,
        pricing_file=None,
        max_cost_per_run=None,
        max_tokens_per_run=None,
        memory=None,
        memory_dir=None,
        memory_retention_days=None,
        agent_mode=None,
        approval_mode=None,
        approval_default=None,
        edit_action_before_run=None,
        checkpoint_dir=None,
        checkpoint_every_step=None,
        multimodal=None,
        max_tokens=None,
        auto=None,
        max_auto_fixes=None,
        stop_on_risk=None,
        require_approval_for_edits=None,
        allow_stub_code_agent=True,
    )

    with patch("builtins.print") as mock_print:
        await run_terminal_command(args)
        any_diagnosed = any("Diagnosed" in call[0][0] for call in mock_print.call_args_list)
        assert any_diagnosed


@pytest.mark.asyncio
async def test_suggested_command_blocked_by_policy(tmp_path):
    # Setup temporary stderr file
    stderr_file = tmp_path / "stderr.log"
    stderr_file.write_text("app.py:15: error: FileNotFoundError: File not found")

    args = Namespace(
        command="terminal",
        terminal_command="suggest",
        stderr_file=str(stderr_file),
        workspace=str(tmp_path),
        config=None,
        agent_id=None,
        provider="openai-compatible",
        model=None,
        base_url=None,
        sandbox=None,
        docker_image=None,
        self_heal=None,
        api_key_env=None,
        timeout=None,
        local_model_timeout=None,
        auto_increase_timeout=None,
        max_retries=None,
        stream=None,
        stream_local_default=None,
        verbose_stream=None,
        tool_calling=None,
        supports_tool_calling=None,
        workspace_mount_path=None,
        temp_base_dir=None,
        sandbox_network=None,
        proxy_url=None,
        loop_timeout=None,
        max_output_chars=None,
        report_output_path=None,
        cache=None,
        no_cache=False,
        cache_dir=None,
        pricing_file=None,
        max_cost_per_run=None,
        max_tokens_per_run=None,
        memory=None,
        memory_dir=None,
        memory_retention_days=None,
        agent_mode=None,
        approval_mode=None,
        approval_default=None,
        edit_action_before_run=None,
        checkpoint_dir=None,
        checkpoint_every_step=None,
        multimodal=None,
        max_tokens=None,
        auto=None,
        max_auto_fixes=None,
        stop_on_risk=None,
        require_approval_for_edits=None,
        allow_stub_code_agent=True,
    )

    # Mock agent suggestion to return a dangerous command (like sudo or rm -rf /)
    mock_agent = MagicMock()
    mock_agent.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "sudo rm -rf /"}}]
        }
    )

    with patch("scripts.llm_harness.providers.create_code_agent", return_value=mock_agent):
        with patch("builtins.print") as mock_print:
            await run_terminal_command(args)
            
            # Policy Engine should block the suggested "sudo rm -rf /" command
            # And it should print a warning
            any_blocked = any(
                "BLOCKED by policy rules" in call[0][0] for call in mock_print.call_args_list
            )
            assert any_blocked
