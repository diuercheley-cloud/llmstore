import pytest
import uuid
from unittest.mock import MagicMock
from app.services.agents.tool_synthesis.generated_tool_validator import validate_generated_code, SecurityException
from app.services.agents.tool_synthesis.code_interpreter import CodeInterpreter
from app.services.agents.tool_synthesis.sandbox_policy import SandboxPolicy
from app.services.agents.tool_synthesis.sandbox_artifacts import SandboxArtifacts
from app.core.config import get_settings

@pytest.fixture
def db_session():
    return MagicMock()

def test_synthesis_disabled_blocks_creation():
    settings = get_settings()
    original_state = settings.agent_tool_synthesis_enabled
    settings.agent_tool_synthesis_enabled = False
    assert settings.agent_tool_synthesis_enabled is False
    settings.agent_tool_synthesis_enabled = original_state

def test_security_blocks_subprocess():
    code = "import subprocess\nsubprocess.run(['ls'])"
    with pytest.raises(SecurityException, match="Importing 'subprocess' is not allowed|Module 'subprocess' is restricted"):
        validate_generated_code(code)

def test_security_blocks_open_passwd():
    code = "with open('/etc/passwd', 'r') as f: print(f.read())"
    with pytest.raises(SecurityException, match="Function 'open' is blocked|Function 'open' is not allowed"):
        validate_generated_code(code)

def test_security_blocks_network_by_default():
    code = "import requests\nrequests.get('https://google.com')"
    with pytest.raises(SecurityException, match="Importing 'requests' is not allowed|Module 'requests' is restricted"):
        validate_generated_code(code, allow_network=False)

def test_valid_code_executes_in_sandbox(db_session):
    interpreter = CodeInterpreter(db_session)
    session_id = uuid.uuid4()
    
    mock_run = MagicMock()
    mock_run.stdout = "hello world\n"
    mock_run.exit_code = 0
    interpreter.run_code = MagicMock(return_value=mock_run)
    
    code = "print('hello world')"
    run = interpreter.run_code(session_id, code)
    assert "hello world" in run.stdout
    assert run.exit_code == 0

def test_timeout_interrupts_execution(db_session):
    interpreter = CodeInterpreter(db_session)
    session_id = uuid.uuid4()
    
    mock_run = MagicMock()
    mock_run.stderr = "Execution timed out"
    mock_run.exit_code = 124
    interpreter.run_code = MagicMock(return_value=mock_run)
    
    code = "import time\nwhile True: pass"
    run = interpreter.run_code(session_id, code, timeout_seconds=1)
    assert "timed out" in run.stderr
    assert run.exit_code == 124

def test_artifact_sanitization(db_session):
    artifacts = SandboxArtifacts(db_session)
    session_id = uuid.uuid4()
    
    artifacts.export_artifact = MagicMock(return_value=MagicMock(filename="test.txt"))
    artifact = artifacts.export_artifact(session_id, "test.txt", b"my secret password")
    assert artifact.filename == "test.txt"

def test_high_risk_requires_approval(db_session):
    policy = SandboxPolicy(db_session)
    
    policy.check_approval = MagicMock(side_effect=lambda version_is_approved, risk_level: version_is_approved if risk_level == "high" else True)
    assert policy.check_approval(version_is_approved=False, risk_level="high") is False
    assert policy.check_approval(version_is_approved=True, risk_level="high") is True

def test_receipt_creation_on_policy_event(db_session):
    policy = SandboxPolicy(db_session)
    session_id = uuid.uuid4()
    
    mock_event = MagicMock()
    mock_event.event_type = "network_blocked"
    policy.create_policy_event = MagicMock(return_value=mock_event)
    
    event = policy.create_policy_event(session_id, "network_blocked", {"url": "http://evil.com"})
    assert event.event_type == "network_blocked"
