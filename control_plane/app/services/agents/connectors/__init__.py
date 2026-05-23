from app.services.agents.connectors.registry import connector_registry
from app.services.agents.connectors.github_connector import GitHubConnector
from app.services.agents.connectors.jira_connector import JiraConnector
from app.services.agents.connectors.slack_connector import SlackConnector
from app.services.agents.connectors.confluence_connector import ConfluenceConnector
from app.services.agents.connectors.salesforce_connector import SalesforceConnector
from app.services.agents.connectors.microsoft365_connector import Microsoft365Connector

# Register connectors
connector_registry.register(GitHubConnector())
connector_registry.register(JiraConnector())
connector_registry.register(SlackConnector())
connector_registry.register(ConfluenceConnector())
connector_registry.register(SalesforceConnector())
connector_registry.register(Microsoft365Connector())
