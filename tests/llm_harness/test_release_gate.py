import os
from unittest.mock import MagicMock, mock_open, patch

# Import target functions
from scripts.llm_harness.release_gate import (
    check_agent_client_real,
    check_ci_harness,
    check_config_invalid,
    check_docker_cleanup,
    check_documentation,
    check_mock_integration,
    check_no_magic_short_circuit,
    check_no_pyc,
    check_secrets_redaction,
    check_typecheck,
    run_release_gate,
)


# 1. Test check_agent_client_real
def test_check_agent_client_real_success():
    with patch("scripts.llm_harness.release_gate.AC", MagicMock(), create=True), \
         patch("scripts.llm_harness.release_gate.OP", MagicMock(), create=True), \
         patch("scripts.llm_harness.release_gate.AP", MagicMock(), create=True), \
         patch("scripts.llm_harness.release_gate.GP", MagicMock(), create=True):
        ok, msg = check_agent_client_real()
        assert ok is True
        assert "present" in msg

def test_check_agent_client_real_failure():
    with patch("builtins.__import__", side_effect=ImportError("mocked import error")):
        ok, msg = check_agent_client_real()
        assert ok is False
        assert "Missing real providers or client facade" in msg


# 2. Test check_docker_cleanup
def test_check_docker_cleanup_success():
    content = "atexit.register signal.signal docker rm -f"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_docker_cleanup()
        assert ok is True
        assert "Docker sandbox implements" in msg

def test_check_docker_cleanup_failure():
    content = "missing cleanup"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_docker_cleanup()
        assert ok is False
        assert "Missing cleanup routines" in msg

def test_check_docker_cleanup_exception():
    with patch("builtins.open", side_effect=FileNotFoundError()):
        ok, msg = check_docker_cleanup()
        assert ok is False
        assert "Failed to check sandbox.py" in msg


# 3. Test check_ci_harness
def test_check_ci_harness_success():
    with patch("os.path.exists", return_value=True):
        ok, msg = check_ci_harness()
        assert ok is True
        assert "valid job" in msg

def test_check_ci_harness_failure():
    with patch("os.path.exists", return_value=False):
        ok, msg = check_ci_harness()
        assert ok is False
        assert "No valid LLM Harness CI workflow" in msg


# 4. Test check_typecheck
def test_check_typecheck_success():
    mock_res = MagicMock()
    mock_res.returncode = 0
    with patch("subprocess.run", return_value=mock_res):
        ok, msg = check_typecheck()
        assert ok is True
        assert "cleanly" in msg

def test_check_typecheck_failure():
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stdout = "error out"
    mock_res.stderr = "error err"
    with patch("subprocess.run", return_value=mock_res):
        ok, msg = check_typecheck()
        assert ok is False
        assert "Type checking failed" in msg

def test_check_typecheck_exception():
    with patch("subprocess.run", side_effect=Exception("command failed")):
        ok, msg = check_typecheck()
        assert ok is False
        assert "Failed to run mypy" in msg


# 5. Test check_config_invalid
def test_check_config_invalid_success():
    content = "HarnessConfigParseError HarnessConfigSchemaError"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_config_invalid()
        assert ok is True
        assert "verified in tests" in msg

def test_check_config_invalid_failure():
    content = "no config errors here"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_config_invalid()
        assert ok is False
        assert "Missing invalid config test coverage" in msg

def test_check_config_invalid_exception():
    with patch("builtins.open", side_effect=Exception("error")):
        ok, msg = check_config_invalid()
        assert ok is False
        assert "Failed to check config tests" in msg


# 6. Test check_secrets_redaction
def test_check_secrets_redaction_success():
    m = mock_open()
    m.side_effect = [
        mock_open(read_data="redact").return_value,
        mock_open(read_data="[REDACTED]").return_value,
    ]
    with patch("builtins.open", m):
        ok, msg = check_secrets_redaction()
        assert ok is True
        assert "verified in test suite" in msg

def test_check_secrets_redaction_failure():
    m = mock_open()
    m.side_effect = [
        mock_open(read_data="nothing").return_value,
        mock_open(read_data="nothing").return_value,
    ]
    with patch("builtins.open", m):
        ok, msg = check_secrets_redaction()
        assert ok is False
        assert "No secrets redaction assertions" in msg

def test_check_secrets_redaction_exception():
    with patch("builtins.open", side_effect=Exception("error")):
        ok, msg = check_secrets_redaction()
        assert ok is False
        assert "Failed to check secrets redaction tests" in msg


# 7. Test check_mock_integration
def test_check_mock_integration_success():
    content = "mock"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_mock_integration()
        assert ok is True
        assert "configured" in msg

def test_check_mock_integration_failure():
    content = "no assertions"
    with patch("builtins.open", mock_open(read_data=content)):
        ok, msg = check_mock_integration()
        assert ok is False
        assert "No mock provider integration tests found" in msg

def test_check_mock_integration_exception():
    with patch("builtins.open", side_effect=Exception("error")):
        ok, msg = check_mock_integration()
        assert ok is False
        assert "Failed to check mock integration tests" in msg


# 8. Test check_documentation
def test_check_documentation_success():
    with patch("os.path.exists", return_value=True):
        ok, msg = check_documentation()
        assert ok is True
        assert "Official documentation" in msg

def test_check_documentation_failure():
    with patch("os.path.exists", return_value=False):
        ok, msg = check_documentation()
        assert ok is False
        assert "Missing official documentation" in msg


# 9. Test check_no_pyc
def test_check_no_pyc_success():
    mock_res = MagicMock()
    mock_res.stdout = ""
    with patch("subprocess.run", return_value=mock_res):
        ok, msg = check_no_pyc()
        assert ok is True
        assert "No versioned compiled files" in msg

def test_check_no_pyc_failure():
    mock_res = MagicMock()
    mock_res.stdout = "foo.pyc\nbar.pyc"
    with patch("subprocess.run", return_value=mock_res):
        ok, msg = check_no_pyc()
        assert ok is False
        assert "Tracked .pyc files found" in msg

def test_check_no_pyc_exception():
    with patch("subprocess.run", side_effect=Exception("error")):
        ok, msg = check_no_pyc()
        assert ok is False
        assert "Failed to check git files" in msg


# 10. Test check_no_magic_short_circuit
def test_check_no_magic_short_circuit_success():
    mock_param = MagicMock()
    mock_param.default = False
    mock_sig = MagicMock()
    mock_sig.parameters = {"allow_test_short_circuit": mock_param}
    with patch("inspect.signature", return_value=mock_sig):
        ok, msg = check_no_magic_short_circuit()
        assert ok is True
        assert "removed/disabled by default" in msg

def test_check_no_magic_short_circuit_failure():
    mock_param = MagicMock()
    mock_param.default = True
    mock_sig = MagicMock()
    mock_sig.parameters = {"allow_test_short_circuit": mock_param}
    with patch("inspect.signature", return_value=mock_sig):
        ok, msg = check_no_magic_short_circuit()
        assert ok is False
        assert "does not default" in msg

def test_check_no_magic_short_circuit_exception():
    with patch("inspect.signature", side_effect=Exception("error")):
        ok, msg = check_no_magic_short_circuit()
        assert ok is False
        assert "Failed to check CodingLoop" in msg


# 11. Test run_release_gate
def test_run_release_gate_all_pass(tmp_path):
    with patch(
        "scripts.llm_harness.release_gate.check_agent_client_real",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_docker_cleanup",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_ci_harness",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_typecheck",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_config_invalid",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_secrets_redaction",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_mock_integration",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_documentation",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_no_pyc",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_no_magic_short_circuit",
        return_value=(True, "OK"),
    ):
        
        with patch("sys.exit") as mock_exit:
            real_join = os.path.join
            def mock_join(a, *args):
                if a == "artifacts/releases/llm-harness":
                    return str(tmp_path / args[0])
                return real_join(a, *args)
                
            with patch("os.path.join", side_effect=mock_join), \
                 patch("os.makedirs"):
                run_release_gate()
                
            mock_exit.assert_called_once_with(0)
            
            report_file = tmp_path / "PRODUCTION_CORE_READINESS.md"
            assert report_file.exists()
            content = report_file.read_text()
            assert "# Production Core Readiness Report" in content
            assert "PASS" in content
            assert "FAIL" not in content

def test_run_release_gate_failures(tmp_path):
    with patch(
        "scripts.llm_harness.release_gate.check_agent_client_real",
        return_value=(False, "FAILED CLIENT"),
    ), patch(
        "scripts.llm_harness.release_gate.check_docker_cleanup",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_ci_harness",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_typecheck",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_config_invalid",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_secrets_redaction",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_mock_integration",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_documentation",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_no_pyc",
        return_value=(True, "OK"),
    ), patch(
        "scripts.llm_harness.release_gate.check_no_magic_short_circuit",
        return_value=(True, "OK"),
    ):
        
        with patch("sys.exit") as mock_exit:
            real_join = os.path.join
            def mock_join(a, *args):
                if a == "artifacts/releases/llm-harness":
                    return str(tmp_path / args[0])
                return real_join(a, *args)
                
            with patch("os.path.join", side_effect=mock_join), \
                 patch("os.makedirs"):
                run_release_gate()
                
            mock_exit.assert_called_once_with(1)
            
            report_file = tmp_path / "PRODUCTION_CORE_READINESS.md"
            assert report_file.exists()
            content = report_file.read_text()
            assert "# Production Core Readiness Report" in content
            assert "FAIL" in content
            assert "FAILED CLIENT" in content
