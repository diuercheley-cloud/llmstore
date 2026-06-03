from unittest.mock import patch

import pytest

from scripts.llm_harness.approval import ApprovalProvider


def test_approval_provider_auto():
    ap = ApprovalProvider(mode="auto")
    assert ap.request_approval({"action_type": "run_shell"}) is True

def test_approval_provider_deny():
    ap = ApprovalProvider(mode="deny")
    assert ap.request_approval({"action_type": "run_shell"}) is False

def test_approval_provider_non_interactive():
    ap = ApprovalProvider(mode="non_interactive", default_policy="allow")
    assert ap.request_approval({"action_type": "run_shell"}) is True
    
    ap = ApprovalProvider(mode="non_interactive", default_policy="deny")
    assert ap.request_approval({"action_type": "run_shell"}) is False

@patch("sys.stdin.isatty", return_value=True)
@patch("builtins.input", side_effect=["y", "n"])
def test_approval_provider_interactive(mock_input, mock_isatty):
    ap = ApprovalProvider(mode="interactive")
    
    # First call: user says 'y'
    assert ap.request_approval({"action_type": "run_shell", "command": "ls"}) is True
    
    # Second call: user says 'n'
    assert ap.request_approval({"action_type": "run_shell", "command": "rm -rf /"}) is False

@patch("sys.stdin.isatty", return_value=True)
@patch("builtins.input", side_effect=["a"])
def test_approval_provider_abort(mock_input, mock_isatty):
    ap = ApprovalProvider(mode="interactive")
    with pytest.raises(InterruptedError, match="User aborted execution"):
        ap.request_approval({"action_type": "run_shell"})
