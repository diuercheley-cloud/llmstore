import pytest
import asyncio
import json
import uuid
from fastapi import FastAPI, Request, Response, Header
from uvicorn import Config, Server
from app.services.agents.connectors.github_connector import GitHubConnector
from app.services.agents.connectors.connector_mode import ConnectorMode
from app.core.config import get_settings

app = FastAPI()

@app.get("/repos/{owner}/{repo}/issues")
async def list_issues(owner: str, repo: str, request: Request, page: int = 1):
    # Simulate pagination
    if page == 1:
        return [{"id": 1, "title": "Issue 1"}, {"id": 2, "title": "Issue 2"}]
    return []

@app.post("/repos/{owner}/{repo}/issues")
async def create_issue(owner: str, repo: str, request: Request, idempotency_key: str = Header(None, alias="Idempotency-Key")):
    body = await request.json()
    return {"id": 123, "title": body["title"], "idempotency_key": idempotency_key}

@pytest.fixture(scope="function")
async def fake_server():
    config = Config(app=app, host="127.0.0.1", port=0, log_level="error")
    server = Server(config)
    task = asyncio.create_task(server.serve())
    
    # Wait for server to start and bind to a port
    while not server.started:
        await asyncio.sleep(0.1)
    
    # Get the assigned port
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    
    server.should_exit = True
    await task

@pytest.mark.asyncio
async def test_github_connector_real_mode_list_issues(fake_server):
    settings = get_settings()
    settings.agent_saas_connectors_enabled = True
    settings.agent_connector_external_network_enabled = True
    settings.agent_connector_real_http_enabled = True
    settings.agent_github_connector_enabled = True
    settings.agent_connector_mode = "real"
    
    connector = GitHubConnector()
    connector.base_url = fake_server
    
    credentials = {"token": "fake-token"}
    params = {"owner": "test-owner", "repo": "test-repo", "limit": 10}
    
    result = await connector.execute("tenant-1", credentials, action="list_issues", params=params)
    
    assert result["mode"] == "real"
    assert len(result["issues"]) == 2
    assert result["issues"][0]["title"] == "Issue 1"

@pytest.mark.asyncio
async def test_github_connector_write_approval_required(fake_server):
    settings = get_settings()
    settings.agent_saas_connectors_enabled = True
    settings.agent_connector_external_network_enabled = True
    settings.agent_connector_real_http_enabled = True
    settings.agent_github_connector_enabled = True
    settings.agent_connector_mode = "real"
    settings.agent_connector_write_enabled = True
    settings.agent_human_approval_enabled = True # Approval REQUIRED
    
    connector = GitHubConnector()
    connector.base_url = fake_server
    
    credentials = {"token": "fake-token"}
    params = {"owner": "test-owner", "repo": "test-repo", "title": "New Issue"}
    
    # Should fail because approval is missing
    with pytest.raises(PermissionError, match="requires human approval"):
        await connector.execute("tenant-1", credentials, action="create_issue", params=params)

@pytest.mark.asyncio
async def test_github_connector_idempotency(fake_server):
    settings = get_settings()
    settings.agent_saas_connectors_enabled = True
    settings.agent_connector_external_network_enabled = True
    settings.agent_connector_real_http_enabled = True
    settings.agent_github_connector_enabled = True
    settings.agent_connector_mode = "real"
    settings.agent_connector_write_enabled = True
    settings.agent_human_approval_enabled = True # Must be true for high-risk
    
    connector = GitHubConnector()
    connector.base_url = fake_server
    
    credentials = {"token": "fake-token"}
    params = {"owner": "test-owner", "repo": "test-repo", "title": "New Issue"}
    
    invocation_id = str(uuid.uuid4())
    result = await connector.execute(
        "tenant-1", 
        credentials, 
        action="create_issue", 
        params=params,
        invocation_id=invocation_id,
        approval_id="approved-123" # Required!
    )
    
    assert result["mode"] == "real"
    assert result["idempotency_key"] == invocation_id
