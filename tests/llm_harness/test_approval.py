from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.llm_harness.approval import ApprovalProvider


def test_approval_provider_auto():
    ap = ApprovalProvider(mode="auto")
    approved, action = ap.request_approval({"action_type": "run_shell"})
    assert approved is True
    assert action["action_type"] == "run_shell"

def test_approval_provider_deny():
    ap = ApprovalProvider(mode="deny")
    approved, _ = ap.request_approval({"action_type": "run_shell"})
    assert approved is False

def test_approval_provider_non_interactive():
    ap = ApprovalProvider(mode="non_interactive", default_policy="allow")
    approved, _ = ap.request_approval({"action_type": "run_shell"})
    assert approved is True
    
    ap = ApprovalProvider(mode="non_interactive", default_policy="deny")
    approved, _ = ap.request_approval({"action_type": "run_shell"})
    assert approved is False

@patch("sys.stdin.isatty", return_value=True)
@patch("builtins.input", side_effect=["y", "n"])
def test_approval_provider_interactive(mock_input, mock_isatty):
    ap = ApprovalProvider(mode="interactive")
    
    # First call: user says 'y'
    approved, _ = ap.request_approval({"action_type": "run_shell", "command": "ls"})
    assert approved is True
    
    # Second call: user says 'n'
    approved, _ = ap.request_approval({"action_type": "run_shell", "command": "rm -rf /"})
    assert approved is False

@patch("sys.stdin.isatty", return_value=True)
@patch("builtins.input", side_effect=["a"])
def test_approval_provider_abort(mock_input, mock_isatty):
    ap = ApprovalProvider(mode="interactive")
    with pytest.raises(InterruptedError, match="User aborted execution"):
        ap.request_approval({"action_type": "run_shell"})

@patch("sys.stdin.isatty", return_value=True)
@patch("builtins.input", side_effect=["e", "y"])
def test_approval_provider_edit(mock_input, mock_isatty, tmp_path, monkeypatch):
    monkeypatch.setenv("EDITOR", "fake-editor")

    def fake_named_tempfile(*args, **kwargs):
        path = tmp_path / "action.json"
        return open(path, "w+", encoding="utf-8")

    def fake_run(cmd, check):
        assert cmd[0] == "fake-editor"
        path = Path(cmd[1])
        path.write_text(
            '{"action_type":"run_shell","command":"echo edited"}',
            encoding="utf-8",
        )

    ap = ApprovalProvider(mode="interactive", edit_action_before_run=True)
    with patch("tempfile.NamedTemporaryFile", side_effect=fake_named_tempfile), patch(
        "subprocess.run",
        side_effect=fake_run,
    ):
        approved, action = ap.request_approval(
            {"action_type": "run_shell", "command": "echo old"}
        )
    assert approved is True
    assert action["command"] == "echo edited"

@patch("sys.stdin.isatty", return_value=False)
def test_approval_provider_interactive_non_tty_requires_default(mock_isatty):
    ap = ApprovalProvider(mode="interactive", default_policy=None)
    with pytest.raises(RuntimeError, match="requires a TTY"):
        ap.request_approval({"action_type": "run_shell"})
