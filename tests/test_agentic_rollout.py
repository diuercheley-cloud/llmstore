import os
import subprocess
import pytest

CONFIG_FILE = "config/agentic.env"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    os.makedirs("config", exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    yield
    # Teardown
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

def get_flag(key):
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r") as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.strip().split("=", 1)[1]
    return None

def set_flag(key, value):
    with open(CONFIG_FILE, "a") as f:
        f.write(f"{key}={value}\n")

def test_pilot_activation_alters_flags():
    result = subprocess.run(["./scripts/activate-agentic-pilot.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    
    assert get_flag("DEPLOYMENT_MODE") == "pilot"
    assert get_flag("AGENT_RUNTIME_ENABLED") == "true"
    assert get_flag("AGENT_STATEFUL_WORKFLOWS_ENABLED") == "true"
    assert get_flag("AGENT_CONNECTOR_WRITE_ENABLED") == "false"
    assert get_flag("AGENT_HUMAN_APPROVAL_ENABLED") == "true"
    assert get_flag("AGENT_STRICT_BUDGETS") == "true"
    assert get_flag("AGENT_EVALS_ENABLED") == "false"

def test_production_activation_requires_readiness():
    # Tenta rodar sem readiness
    result = subprocess.run(["./scripts/activate-agentic-production.sh"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Readiness check not passed" in result.stdout

    # Habilita readiness mas não SLOs
    set_flag("AGENTIC_READINESS_STATUS", "passed")
    result = subprocess.run(["./scripts/activate-agentic-production.sh"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "SLO check not passed" in result.stdout

    # Habilita tudo e roda
    set_flag("AGENTIC_SLO_STATUS", "passed")
    set_flag("AGENTIC_BUDGET_STATUS", "passed")
    result = subprocess.run(["./scripts/activate-agentic-production.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert get_flag("DEPLOYMENT_MODE") == "production"
    assert get_flag("AGENT_EVALS_ENABLED") == "true"
    assert get_flag("AGENT_WORKER_AUTOSCALING_ENABLED") == "true"
    assert get_flag("AGENT_PROMOTION_REQUIRES_EVALS") == "true"
    assert get_flag("AGENT_EVAL_REGRESSION_GATE_ENABLED") == "true"

def test_rollback_drains_queue_and_preserves_workflows():
    result = subprocess.run(["./scripts/rollback-agentic-runtime.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    
    # rollback drena queue
    assert get_flag("AGENT_ROLLOUT_QUEUE_STATUS") == "drained"
    
    # rollback preserva stateful workflows
    assert get_flag("AGENT_ROLLOUT_WORKFLOWS_STATE") == "preserved"
    assert get_flag("AGENT_RUNTIME_ENABLED") == "false"
    assert get_flag("AGENT_ROLLOUT_NEW_RUNS") == "paused"
