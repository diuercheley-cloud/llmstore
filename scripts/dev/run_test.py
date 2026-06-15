import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.llm_harness.providers import _PROBE_CACHE, create_code_agent


async def run():
    _PROBE_CACHE.clear()
    agent = create_code_agent(
        "local-openai-compatible",
        {"agent_id": "test", "base_url": "http://fake/v1", "model": "model-1"},
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {"data": [{"id": "model-1"}]}

    mock_probe_response = MagicMock()
    mock_probe_response.status_code = 200
    mock_probe_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "final",
                                "arguments": '{"message":"native_probe_ok"}',
                            },
                        }
                    ]
                }
            }
        ]
    }

    async def fake_request(method, url, **kwargs):
        if method == "GET":
            return mock_models_response
        return mock_probe_response

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        health = await agent.health_check()
        print(json.dumps(health["details"]["native_tool_calling_probe"], indent=2))


asyncio.run(run())
