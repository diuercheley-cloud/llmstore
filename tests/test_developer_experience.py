import os
import shutil
import uuid

import pytest
from app.services.plugins.dev_kit import PluginHarness

from scripts.agentctl import AgentCTL


@pytest.fixture
def test_dir():
    path = f"test_agent_{uuid.uuid4().hex}"
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)
    if os.path.exists(f"{path}.zip"):
        os.remove(f"{path}.zip")

def test_agentctl_init_and_validate(test_dir):
    ctl = AgentCTL()
    
    # 1. Init
    ctl.init(test_dir, "support-triage")
    assert os.path.exists(os.path.join(test_dir, "agent.yaml"))
    
    # 2. Validate
    # Should not raise SystemExit
    ctl.validate(test_dir)

def test_agentctl_bundle(test_dir):
    ctl = AgentCTL()
    ctl.init(test_dir, "support-triage")
    
    bundle_path = f"{test_dir}.zip"
    ctl.bundle(test_dir, bundle_path)
    assert os.path.exists(bundle_path)

def test_plugin_harness_validation():
    # Use the example plugin
    manifest_path = "examples/plugins/safe-tool/plugin.json"
    harness = PluginHarness(manifest_path)
    
    assert harness.validate()
    
    result = harness.dry_run_tool("calculate_hash", {"text": "hello"})
    assert result["status"] == "success"
    assert "Dry-run" in result["data"]

def test_agent_template_content():
    template_path = "examples/agents/support-triage/agent.yaml"
    assert os.path.exists(template_path)
    with open(template_path, "r") as f:
        content = f.read()
        assert "support-triage" in content
        assert "gpt-4" in content
