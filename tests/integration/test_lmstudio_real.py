"""
Real integration test for LM Studio local execution.

To run this test:
pytest -m local_llm tests/integration/test_lmstudio_real.py

It requires LM Studio to be running locally with the following environment variables (or defaults):
LM_STUDIO_BASE_URL (default: http://192.168.101.1:1234/v1)
LM_STUDIO_MODEL (default: nvidia/nemotron-3-nano-4b)
"""

import os
import httpx
import pytest

LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://192.168.101.1:1234/v1")
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "nvidia/nemotron-3-nano-4b")
LM_STUDIO_API_KEY = os.environ.get("LM_STUDIO_API_KEY", "lm-studio")

@pytest.mark.local_llm
@pytest.mark.asyncio
async def test_lmstudio_real_chat_completion():
    # Only run this test if explicitly requested via environment variables or defaults
    if not os.environ.get("LM_STUDIO_BASE_URL") and not os.environ.get("LM_STUDIO_MODEL"):
        pytest.skip("LM_STUDIO_BASE_URL or LM_STUDIO_MODEL not explicitly set, skipping real integration test by default.")

    # Check if the server is actually up to avoid failing tests when just skipping was intended
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{LM_STUDIO_BASE_URL}/models")
            if resp.status_code != 200:
                 pytest.skip(f"LM Studio server at {LM_STUDIO_BASE_URL} returned {resp.status_code}, skipping.")
    except Exception as e:
        pytest.skip(f"Could not connect to LM Studio at {LM_STUDIO_BASE_URL}: {e}")

    headers = {
        "Authorization": f"Bearer {LM_STUDIO_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'hello world' and nothing else."}
        ],
        "temperature": 0.0,
        "max_tokens": 50
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{LM_STUDIO_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        content = data["choices"][0]["message"]["content"]
        assert content is not None
        assert len(content.strip()) > 0
        assert "hello" in content.lower()
