import os
import shutil
import tempfile

import httpx
import pytest

@pytest.fixture(autouse=True)
def clear_probe_cache():
    from scripts.llm_harness.providers import _PROBE_CACHE
    _PROBE_CACHE.clear()

from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.providers import StubProvider


@pytest.fixture
def temp_repo():
    """Creates a temporary repository directory with simple python file and test."""
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo")
    os.makedirs(repo_dir)
    
    # Create simple app.py
    with open(os.path.join(repo_dir, "app.py"), "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
        
    # Create test_app.py
    with open(os.path.join(repo_dir, "test_app.py"), "w") as f:
        f.write("from app import add\ndef test_add():\n    assert add(2, 3) == 5\n")
        
    yield repo_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def fake_provider():
    """Returns a StubProvider instance with default configuration."""
    return StubProvider({"agent_id": "stub-agent"})

@pytest.fixture
def mock_openai_transport():
    """Returns a mock transport configured to return valid OpenAI chat completion response."""
    def handler(request: httpx.Request) -> httpx.Response:
        resp = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": '{"type": "final", "reason": "test final", "payload": {"message": "ok"}}'
                }
            }],
            "usage": {"total_tokens": 10}
        }
        return httpx.Response(200, json=resp)
    return httpx.MockTransport(handler)

@pytest.fixture
def mock_control_plane_transport():
    """Returns a mock transport simulating ControlPlaneProvider agent endpoints."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/v1/agents":
            return httpx.Response(200, json=[{"id": "agent-1"}])
        if request.url.path == "/v1/agents/agent-1/runs":
            return httpx.Response(200, json={"id": "run-1"})
        if request.url.path == "/v1/agents/runs/run-1/events":
            events = (
                'event: run.completed\n'
                'data: {"output":{"type":"final","payload":{"message":"ok"}}}\n\n'
            )
            return httpx.Response(200, text=events)
        return httpx.Response(404)
    return httpx.MockTransport(handler)

@pytest.fixture
def sample_harness_config():
    """Returns a default HarnessConfig instance."""
    return HarnessConfig(
        code_agent="stub",
        model="test-model",
        sandbox=False,
    )

@pytest.fixture
def no_secrets_assertion():
    """Returns a helper function that asserts no secrets exist in the provided text content."""
    def _assert_no_secrets(content: str, secrets: list[str] = None):
        if secrets is None:
            secrets = ["sk-", "password", "secret", "private_key", "authorization"]
        for secret in secrets:
            assert secret not in content, f"Secret leak detected: '{secret}' found in content"
    return _assert_no_secrets

@pytest.fixture
def isolated_cache_dir():
    """Yields a temporary path isolated for caching."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def isolated_memory_dir():
    """Yields a temporary path isolated for persistent memory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
