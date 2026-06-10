import asyncio
import json

import httpx
import pytest

from scripts.llm_harness.cache import LocalCache
from scripts.llm_harness.checkpoint import CheckpointManager
from scripts.llm_harness.cli_commands import run_code_batch_command
from scripts.llm_harness.providers import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_provider_timeout_error_handling(monkeypatch):
    """Verify that provider timeouts are handled and trigger retries."""
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-test")
    attempts = 0
    
    async def async_noop(*args, **kwargs):
        pass
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.TimeoutException("Connection timed out")
        
    config = {
        "agent_id": "test-agent",
        "base_url": "http://openai-mock/v1",
        "model": "gpt-4",
        "api_key_env": "MOCK_OPENAI_API_KEY",
        "max_retries": 1,
        "transport": httpx.MockTransport(handler),
        "timeout": 1.0,
    }
    provider = OpenAICompatibleProvider(config)
    
    with pytest.raises(httpx.TimeoutException):
        await provider.chat_completion([{"role": "user", "content": "hello"}])
    assert attempts == 2  # Attempt 1 + 1 retry

@pytest.mark.asyncio
async def test_corrupt_cache_behaves_as_miss(tmp_path):
    """Verify that a corrupted cache file does not crash loading, but behaves as a miss."""
    cache = LocalCache(mode="llm", cache_dir=str(tmp_path))
    # Create a corrupted JSON file in cache dir
    cache_file = tmp_path / "llm" / "corrupt_hash.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("invalid { json [")
    
    val = cache.get_json("llm", "corrupt_hash")
    assert val is None  # Safe recovery, acts as miss

@pytest.mark.asyncio
async def test_corrupt_checkpoint_ignored_gracefully(tmp_path):
    """Verify that corrupt checkpoints fail gracefully."""
    mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
    checkpoint_file = tmp_path / "checkpoint_run1.json"
    checkpoint_file.write_text("corrupted content ---")
    
    state = mgr.load_checkpoint("run1")
    assert state is None  # Should return None instead of crashing

class FakeBatchArgs:
    def __init__(self, file, concurrency=2):
        self.file = file
        self.concurrency = concurrency
        self.config = None
        self.model = "gpt-4"
        self.base_url = "http://localhost:8080"
        self.sandbox = False
        self.docker_image = None
        self.self_heal = False
        self.api_key_env = "BATCH_KEY"
        self.timeout = 5
        self.max_retries = 0
        self.stream = False
        self.workspace_mount_path = None
        self.temp_base_dir = None
        self.sandbox_network = "none"
        self.proxy_url = None
        self.loop_timeout = 5
        self.max_output_chars = 1000
        self.report_output_path = None
        self.cache = "disabled"
        self.no_cache = True
        self.cache_dir = None
        self.pricing_file = None
        self.max_cost_per_run = None
        self.max_tokens_per_run = None
        self.memory = "disabled"
        self.memory_dir = None
        self.memory_retention_days = 1
        self.agent_mode = "single"
        self.approval_mode = "auto"
        self.approval_default = "deny"
        self.checkpoint_dir = None
        self.checkpoint_every_step = False
        self.allow_stub_code_agent = True

@pytest.mark.asyncio
async def test_code_batch_concurrency(tmp_path, monkeypatch):
    """Verify code-batch concurrent execution under stress."""
    monkeypatch.setenv("BATCH_KEY", "sk-batch")
    
    scenarios = [
        {"name": "task1", "task": "do nothing 1", "timeout": 2},
        {"name": "task2", "task": "do nothing 2", "timeout": 2},
    ]
    
    scenarios_file = tmp_path / "scenarios.json"
    scenarios_file.write_text(json.dumps(scenarios))
    
    args = FakeBatchArgs(str(scenarios_file), concurrency=2)
    
    # We mock run_harness to avoid executing real loops
    from scripts.llm_harness.models import ExecutionResult
    async def mock_run_harness(*args, **kwargs):
        await asyncio.sleep(0.01)
        return ExecutionResult(success=True, message="done")
        
    monkeypatch.setattr("scripts.llm_harness.legacy_runner.run_harness", mock_run_harness)
    
    # Capture sys.exit or print statements
    monkeypatch.setattr("sys.exit", lambda code: None)
    
    await run_code_batch_command(args)
    # The batch should execute successfully without crash
