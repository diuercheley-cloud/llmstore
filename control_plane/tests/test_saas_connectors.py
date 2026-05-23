import pytest
import os
from unittest.mock import patch
from app.services.agents.connectors.registry import connector_registry
from app.services.agents.connectors.github_connector import GitHubConnector
from app.services.agents.connectors.slack_connector import SlackConnector
from app.services.agents.connectors.base import ConnectorCapability
from app.core.config import get_settings

def patch_settings(env_dict):
    """Helper to patch environment and clear settings cache."""
    patcher = patch.dict(os.environ, env_dict)
    patcher.start()
    get_settings.cache_clear()
    return patcher

@pytest.fixture(autouse=True)
def setup_connectors():
    get_settings.cache_clear()
    connector_registry.clear()
    connector_registry.register(GitHubConnector())
    connector_registry.register(SlackConnector())
    yield
    connector_registry.clear()
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_connector_registry_lists_connectors():
    connectors = connector_registry.list_connectors()
    assert len(connectors) >= 2
    names = [c.connector_name for c in connectors]
    assert "github" in names
    assert "slack" in names

@pytest.mark.asyncio
async def test_write_action_blocked_by_default():
    github = connector_registry.get_connector("github")
    
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "true",
        "AGENT_CONNECTOR_WRITE_ENABLED": "false"
    })
    try:
        with pytest.raises(PermissionError, match="Write capability 'create' is disabled"):
            await github.execute("tenant1", {}, action="create_issue", params={})
    finally:
        p.stop()

@pytest.mark.asyncio
async def test_external_network_disabled_blocks_calls():
    github = connector_registry.get_connector("github")
    
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "false"
    })
    try:
        with pytest.raises(PermissionError, match="External network access for connectors is disabled"):
            await github.execute("tenant1", {}, action="get_issue", params={"issue_id": "1"})
    finally:
        p.stop()

@pytest.mark.asyncio
async def test_dry_run_no_side_effect():
    github = connector_registry.get_connector("github")
    
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "true",
        "AGENT_CONNECTOR_WRITE_ENABLED": "false"
    })
    try:
        result = await github.dry_run("tenant1", {}, action="create_issue", params={})
        assert result["status"] == "dry_run_success"
    finally:
        p.stop()

@pytest.mark.asyncio
async def test_github_mock_search_works():
    github = connector_registry.get_connector("github")
    
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "true"
    })
    try:
        result = await github.execute("tenant1", {}, action="search_repositories")
        assert "repositories" in result
        assert result["repositories"][0]["name"] == "repo1"
    finally:
        p.stop()

@pytest.mark.asyncio
async def test_slack_post_message_requires_write_enabled():
    slack = connector_registry.get_connector("slack")
    
    # 1. Disabled
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "true",
        "AGENT_CONNECTOR_WRITE_ENABLED": "false"
    })
    try:
        with pytest.raises(PermissionError):
            await slack.execute("tenant1", {}, action="post_message", params={"text": "hi"})
    finally:
        p.stop()
            
    # 2. Enabled
    p = patch_settings({
        "AGENT_SAAS_CONNECTORS_ENABLED": "true", 
        "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": "true",
        "AGENT_CONNECTOR_WRITE_ENABLED": "true"
    })
    try:
        result = await slack.execute("tenant1", {}, action="post_message", params={"text": "hi"})
        assert result["status"] == "success"
    finally:
        p.stop()
