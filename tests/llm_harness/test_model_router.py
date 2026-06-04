import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.model_router import ModelRouter, is_cloud_provider


def test_is_cloud_provider():
    assert is_cloud_provider("openai-compatible") is True
    assert is_cloud_provider("anthropic") is True
    assert is_cloud_provider("google") is True
    assert is_cloud_provider("control-plane") is True
    assert is_cloud_provider("local-openai-compatible") is False
    assert is_cloud_provider("stub") is False


def test_profile_resolution_and_routing():
    config_dict = {
        "models": {
            "default": "local-qwen",
            "profiles": {
                "local-qwen": {
                    "provider": "local-openai-compatible",
                    "model": "qwen/qwen3.6-35b-a3b",
                    "base_url": "http://localhost:1234/v1",
                    "timeout": 300,
                    "api_key": "dummy-local-key"
                },
                "cloud-fast": {
                    "provider": "openai-compatible",
                    "model": "gpt-4o-mini",
                    "api_key": "AKIA1234567890123456"
                }
            },
            "routing": {
                "bugfix": "local-qwen",
                "multimodal": "cloud-fast"
            }
        }
    }
    config = HarnessConfig(**config_dict)
    router = ModelRouter(config)

    # Resolve profiles
    assert router.resolve_profile("local-qwen")["model"] == "qwen/qwen3.6-35b-a3b"
    assert router.resolve_profile("cloud-fast")["provider"] == "openai-compatible"
    assert router.resolve_profile("non-existent") is None

    # Resolve by task type
    name, profile = router.resolve_by_task_type("bugfix")
    assert name == "local-qwen"
    assert profile["model"] == "qwen/qwen3.6-35b-a3b"

    name, profile = router.resolve_by_task_type("multimodal")
    assert name == "cloud-fast"

    # Default fallback routing
    name, profile = router.resolve_by_task_type("unknown-task")
    assert name == "local-qwen"


def test_cloud_model_policy():
    # 1. Cloud models allowed (default)
    config = HarnessConfig(
        models={
            "profiles": {
                "cloud": {"provider": "openai-compatible", "model": "gpt-4o"}
            }
        },
        allow_cloud_models=True
    )
    router = ModelRouter(config)
    profile = router.resolve_profile("cloud")
    assert router.check_policy(profile) is True

    # 2. Cloud models blocked
    config_blocked = HarnessConfig(
        models={
            "profiles": {
                "cloud": {"provider": "openai-compatible", "model": "gpt-4o"}
            }
        },
        allow_cloud_models=False
    )
    router_blocked = ModelRouter(config_blocked)
    assert router_blocked.check_policy(profile) is False


@pytest.mark.asyncio
@patch("scripts.llm_harness.model_router.create_code_agent")
async def test_fallback_on_transient_error(mock_create_agent):
    config = HarnessConfig(
        models={
            "profiles": {
                "primary": {"provider": "stub", "model": "primary-model"},
                "fallback": {"provider": "stub", "model": "fallback-model"}
            }
        }
    )
    router = ModelRouter(config)

    # Mock primary agent failing, fallback agent succeeding
    mock_agent_primary = MagicMock()
    mock_agent_primary.chat_completion = AsyncMock(
        side_effect=RuntimeError("Timeout error")
    )

    mock_agent_fallback = MagicMock()
    mock_agent_fallback.chat_completion = AsyncMock(return_value="fallback_success")

    def create_agent_side_effect(provider, cfg):
        if cfg.get("model") == "primary-model":
            return mock_agent_primary
        return mock_agent_fallback

    mock_create_agent.side_effect = create_agent_side_effect

    res = await router.chat_completion_with_fallback(
        messages=[{"role": "user", "content": "hello"}],
        profile_name="primary",
        fallback_profile_name="fallback"
    )

    assert res == "fallback_success"
    assert mock_agent_primary.chat_completion.call_count == 1
    assert mock_agent_fallback.chat_completion.call_count == 1


@pytest.mark.asyncio
@patch("scripts.llm_harness.model_router.create_code_agent")
async def test_policy_cloud_blocked_raises_permission_error(mock_create_agent):
    config = HarnessConfig(
        models={
            "profiles": {
                "cloud": {"provider": "openai-compatible", "model": "gpt-4o"}
            }
        },
        allow_cloud_models=False
    )
    router = ModelRouter(config)

    with pytest.raises(PermissionError, match="blocked by policy"):
        await router.chat_completion_with_fallback(
            messages=[{"role": "user", "content": "hello"}],
            profile_name="cloud"
        )


def test_estimate_cost():
    config = HarnessConfig()
    router = ModelRouter(config)

    # 1. Local/stub provider cost
    cost_local = router.estimate_cost({"provider": "stub", "model": "primary-model"})
    assert cost_local["prompt_token_price_per_1m"] == 0.0
    assert cost_local["is_local"] is True

    # 2. Known cloud model cost
    cost_gpt4o = router.estimate_cost({"provider": "openai-compatible", "model": "gpt-4o"})
    assert cost_gpt4o["prompt_token_price_per_1m"] == 5.0
    assert cost_gpt4o["is_local"] is False

    # 3. Unknown cloud model cost
    cost_unknown = router.estimate_cost(
        {"provider": "openai-compatible", "model": "unknown-model"}
    )

    assert cost_unknown["prompt_token_price_per_1m"] == 10.0
    assert cost_unknown["is_local"] is False


@pytest.mark.asyncio
@patch("scripts.llm_harness.model_router.create_code_agent")
async def test_fallback_fails_both(mock_create_agent):
    config = HarnessConfig(
        models={
            "profiles": {
                "primary": {"provider": "stub", "model": "primary-model"},
                "fallback": {"provider": "stub", "model": "fallback-model"}
            }
        }
    )
    router = ModelRouter(config)

    mock_agent = MagicMock()
    mock_agent.chat_completion = AsyncMock(side_effect=RuntimeError("Transient error"))
    mock_create_agent.return_value = mock_agent

    with pytest.raises(RuntimeError, match="Transient error"):
        await router.chat_completion_with_fallback(
            messages=[{"role": "user", "content": "hello"}],
            profile_name="primary",
            fallback_profile_name="fallback"
        )


@pytest.mark.asyncio
@patch("scripts.llm_harness.model_router.create_code_agent")
async def test_fallback_default_config_resolution(mock_create_agent):
    config = HarnessConfig(
        provider="stub",
        model="global-model"
    )
    router = ModelRouter(config)

    mock_agent = MagicMock()
    mock_agent.chat_completion = AsyncMock(return_value="fallback_success")
    mock_create_agent.return_value = mock_agent

    res = await router.chat_completion_with_fallback(
        messages=[{"role": "user", "content": "hello"}]
    )
    assert res == "fallback_success"


def test_resolve_by_task_type_default_fallback():
    config = HarnessConfig(provider="google", model="gemini-2.5-flash")
    router = ModelRouter(config)

    name, profile = router.resolve_by_task_type("any-task")
    assert name == "default-config"
    assert profile["provider"] == "google"
    assert profile["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_non_existent_profile_raises_value_error():
    config = HarnessConfig()
    router = ModelRouter(config)

    with pytest.raises(ValueError, match="not found in configuration"):
        await router.chat_completion_with_fallback(
            messages=[{"role": "user", "content": "hello"}],
            profile_name="non-existent"
        )


@pytest.mark.asyncio
async def test_non_existent_fallback_profile_raises_value_error():
    config = HarnessConfig(
        models={
            "profiles": {
                "primary": {"provider": "stub", "model": "primary-model"}
            }
        }
    )
    router = ModelRouter(config)

    with patch("scripts.llm_harness.model_router.create_code_agent") as mock_create:
        mock_agent = MagicMock()
        mock_agent.chat_completion = AsyncMock(side_effect=RuntimeError("Fail"))
        mock_create.return_value = mock_agent

        with pytest.raises(ValueError, match="Fallback model profile 'non-existent' not found"):
            await router.chat_completion_with_fallback(
                messages=[{"role": "user", "content": "hello"}],
                profile_name="primary",
                fallback_profile_name="non-existent"
            )


def test_policy_models_config_dict():
    class SimpleConfig:
        def __init__(self):
            self.models = {
                "allow_cloud_models": False
            }
    config = SimpleConfig()
    router = ModelRouter(config)
    assert router.check_policy({"provider": "openai-compatible"}) is False
    assert router.check_policy({"provider": "stub"}) is True

