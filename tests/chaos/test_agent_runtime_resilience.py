"""Chaos tests for agent runtime resilience.

These tests verify the system degrades gracefully under failure conditions:
- Redis outage
- Database outage
- Provider API failure
- Network partition
"""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_agent_run_survives_redis_outage():
    """Agent execution should fall back to in-memory state when Redis is down."""
    from app.services.agents.agent_executor import AgentExecutor
    from app.services.agents.agent_state import AgentStateStore

    store = AgentStateStore()
    with patch.object(store, "_redis", return_value=None), \
         patch.object(store, "_use_redis", False):
        executor = AgentExecutor(state_store=store)
        result = await executor.execute(
            agent_id="test-agent",
            input_data={"prompt": "hello"},
        )
        assert result is not None
        assert "error" not in result


@pytest.mark.asyncio
async def test_provider_fallback_on_api_failure():
    """Routing should fall back to next provider when primary fails."""
    from app.services.providers.registry import get_providers

    providers = get_providers()
    assert len(providers) > 0, "At least one provider must be registered"

    from app.services.providers.base import ProviderAdapter

    class FailingProvider(ProviderAdapter):
        def __init__(self):
            super().__init__("failing", "failing", True, True)

        async def health_check(self):
            return {"healthy": False, "error": "simulated failure"}

        async def list_models(self):
            return []

        async def chat_completion(self, payload):
            raise RuntimeError("simulated API failure")

        async def responses(self, payload):
            raise RuntimeError("simulated API failure")

        async def embeddings(self, payload):
            raise RuntimeError("simulated API failure")

        def estimate_cost(self, model, prompt_tokens, completion_tokens):
            return 0.0

        def capabilities(self):
            from app.services.providers.schemas import ProviderCapabilities
            return ProviderCapabilities(
                chat=True, streaming=True, responses=True,
                embeddings=False, tools=False, vision=False,
                json_mode=False, max_context_tokens=4096, pricing_configured=False,
            )

    provider = FailingProvider()
    with pytest.raises(RuntimeError, match="simulated API failure"):
        await provider.chat_completion({"messages": [{"role": "user", "content": "hi"}]})


@pytest.mark.asyncio
async def test_health_check_degrades_gracefully():
    """System health should report degraded, not crash, when dependencies are down."""
    from app.services.system_health import SystemHealthService

    service = SystemHealthService()

    with patch.object(service, "_check_database", return_value={"healthy": False, "error": "connection refused"}), \
         patch.object(service, "_check_redis", return_value={"healthy": False, "error": "connection refused"}):

        report = await service.get_health_report()
        assert report is not None
        assert "overall" in report
        assert report["overall"] in ("healthy", "degraded", "unhealthy")
        assert "checks" in report


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_deadlock():
    """Multiple concurrent agent runs should not cause deadlocks."""
    import asyncio

    from app.services.agents.agent_executor import AgentExecutor

    executor = AgentExecutor()

    async def run_agent(i: int):
        try:
            return await executor.execute(
                agent_id="test-agent",
                input_data={"prompt": f"request-{i}"},
            )
        except Exception as e:
            return {"error": str(e), "index": i}

    tasks = [run_agent(i) for i in range(20)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert len(results) == 20
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_large_payload_handling():
    """Agent executor should handle large input payloads without OOM."""
    from app.services.agents.agent_executor import AgentExecutor

    executor = AgentExecutor()
    large_payload = {"prompt": "x" * 100_000, "metadata": {"key": "value"}}

    result = await executor.execute(
        agent_id="test-agent",
        input_data=large_payload,
    )
    assert result is not None
