import uuid
from unittest.mock import MagicMock, patch

import pytest
from kleberai import Client


@pytest.fixture
def client():
    return Client(api_key="test-key")


def test_agents_list(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "agent-1"}]
        mock_request.return_value = mock_response

        agents = client.agents.list()
        assert len(agents) == 1
        assert agents[0]["id"] == "agent-1"
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        # Updated to check for /v1/ prefix
        assert args[1] == "http://localhost:18080/v1/agents"


def test_agents_run(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"run_id": "run-1"}
        mock_request.return_value = mock_response

        agent_id = str(uuid.uuid4())
        run = client.agents.run(agent_id=agent_id, input_data={"query": "test"})
        assert run["run_id"] == "run-1"
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        # Updated to check for /v1/ and /runs (plural)
        assert f"/v1/agents/{agent_id}/runs" in args[1]
