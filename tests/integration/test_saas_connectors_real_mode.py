from unittest.mock import MagicMock, patch

import pytest
from app.services.agents.connectors.connector_mode import ConnectorMode
from app.services.agents.connectors.github_connector import GitHubConnector


@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.core.config.get_settings") as mock:
        settings = MagicMock()
        settings.agent_saas_connectors_enabled = True
        settings.agent_connector_external_network_enabled = True
        settings.agent_connector_write_enabled = True
        settings.agent_iam_enabled = False  # Disable IAM check for simplicity in these tests
        mock.return_value = settings
        yield settings


@pytest.fixture(autouse=True)
def mock_audit():
    with patch("app.services.agents.connectors.base.ConnectorAdapter.audit_connector_call") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.mark.asyncio
async def test_github_connector_mock_mode(mock_settings):
    connector = GitHubConnector()
    mock_settings.agent_connector_mode = "mock"
    result = await connector.execute(
        tenant_id="test_tenant", credentials={}, action="get_issue", params={"issue_id": "123"}
    )
    assert result["mock"] is True
    assert result["issue"]["id"] == "123"


@pytest.mark.asyncio
async def test_github_connector_real_mode_blocked_if_http_disabled(mock_settings):
    connector = GitHubConnector()
    mock_settings.agent_connector_mode = "real"
    mock_settings.agent_github_connector_enabled = True
    mock_settings.agent_connector_real_http_enabled = False

    with pytest.raises(PermissionError) as excinfo:
        await connector.execute(
            tenant_id="test_tenant",
            credentials={"token": "fake_token"},
            action="get_issue",
            params={"owner": "org", "repo": "repo", "issue_number": "1"},
        )
    assert "Real HTTP calls are disabled globally" in str(excinfo.value)


@pytest.mark.asyncio
async def test_github_connector_real_mode_blocked_if_no_creds(mock_settings):
    connector = GitHubConnector()
    mock_settings.agent_connector_mode = "real"
    mock_settings.agent_github_connector_enabled = True
    mock_settings.agent_connector_real_http_enabled = True

    with pytest.raises(ValueError) as excinfo:
        await connector.execute(
            tenant_id="test_tenant",
            credentials={},
            action="get_issue",
            params={"owner": "org", "repo": "repo", "issue_number": "1"},
        )
    assert "Missing required credentials" in str(excinfo.value)


@pytest.mark.asyncio
async def test_github_connector_real_mode_http_call(mock_settings):
    connector = GitHubConnector()
    mock_settings.agent_connector_mode = "real"
    mock_settings.agent_github_connector_enabled = True
    mock_settings.agent_connector_real_http_enabled = True

    with patch("app.services.agents.connectors.http_client.httpx.AsyncClient") as mock_client_class:
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Real Issue"}
        mock_client.request.return_value = mock_response

        # This is a bit tricky because of the async context manager
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await connector.execute(
            tenant_id="test_tenant",
            credentials={"token": "real_token"},
            action="get_issue",
            params={"owner": "org", "repo": "repo", "issue_number": "1"},
        )

        assert result["id"] == 1
        assert result.get("mock") is None

        # Verify URL
        mock_client.request.assert_called_once()
        args, kwargs = mock_client.request.call_args
        assert kwargs["url"] == "https://api.github.com/repos/org/repo/issues/1"
        assert kwargs["headers"]["Authorization"] == "token real_token"


@pytest.mark.asyncio
async def test_audit_logging(mock_audit, mock_settings):
    connector = GitHubConnector()
    mock_settings.agent_connector_mode = "mock"
    await connector.execute(
        tenant_id="test_tenant", credentials={}, action="get_issue", params={"issue_id": "123"}
    )
    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[2] == "get_issue"
    assert args[3]["mode"] == ConnectorMode.MOCK
