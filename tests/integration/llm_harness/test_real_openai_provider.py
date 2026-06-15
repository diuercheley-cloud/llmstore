import json

import httpx
import pytest

from scripts.llm_harness.providers import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_provider_real_call_mocked(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "sk-test")

    # Mock response from "real" OpenAI-compatible server
    def handler(request):
        if request.url.path == "/v1/chat/completions":
            resp_data = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "type": "plan",
                                    "reason": "test plan",
                                    "payload": {"steps": ["step 1"]},
                                }
                            ),
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
            return httpx.Response(200, content=json.dumps(resp_data))
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    config = {
        "agent_id": "test-agent",
        "base_url": "http://mock-api.com/v1",
        "model": "gpt-4o",
        "api_key_env": "MOCK_KEY",
        "transport": transport,
    }

    provider = OpenAICompatibleProvider(config)

    messages = [{"role": "user", "content": "hello"}]
    response = await provider.chat_completion(messages)

    assert "choices" in response
    content = response["choices"][0]["message"]["content"]
    content_json = json.loads(content)
    assert content_json["action_type"] == "plan"
    assert response["usage"]["total_tokens"] == 30
