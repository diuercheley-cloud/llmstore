import pytest

from app.services.agents.connectors.confluence_connector import ConfluenceConnector
from app.services.agents.connectors.jira_connector import JiraConnector
from app.services.agents.connectors.microsoft365_connector import Microsoft365Connector
from app.services.agents.connectors.salesforce_connector import SalesforceConnector


@pytest.mark.asyncio
async def test_confluence_connector_mock_execution():
    connector = ConfluenceConnector()

    result = await connector._execute_mock("search_pages", {})

    assert result["connector"] == "confluence"
    assert result["mode"] == "mock"
    assert result["mock"] is True
    assert result["pages"][0]["title"] == "Design Doc"


@pytest.mark.asyncio
async def test_jira_connector_mock_execution():
    connector = JiraConnector()

    result = await connector._execute_mock("get_issue", {"issue_key": "PROJ-42"})

    assert result["connector"] == "jira"
    assert result["issue"]["key"] == "PROJ-42"


@pytest.mark.asyncio
async def test_microsoft365_connector_mock_execution():
    connector = Microsoft365Connector()

    result = await connector._execute_mock("get_calendar_events_metadata", {})

    assert result["connector"] == "microsoft365"
    assert result["events"][0]["subject"] == "Sprint Planning"


@pytest.mark.asyncio
async def test_salesforce_connector_mock_execution():
    connector = SalesforceConnector()

    result = await connector._execute_mock("search_accounts", {})

    assert result["connector"] == "salesforce"
    assert result["accounts"][0]["name"] == "Acme Corp"
