import logging
from typing import Any

from .cache import LocalCache
from .providers import create_code_agent

logger = logging.getLogger(__name__)


class AgentClient:
    """
    Client facade that delegates interactions to the registered CodeAgentProvider.
    """

    def __init__(
        self,
        agent_id: str,
        base_url: str = "",
        provider: str = "stub",
        model: str = "",
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 30.0,
        local_model_timeout: float = 300.0,
        auto_increase_timeout: bool = False,
        max_retries: int = 3,
        stream: bool = False,
        stream_local_default: bool = True,
        verbose_stream: bool = False,
        tool_calling: str = "auto",
        supports_tool_calling: bool = False,
        allow_native_tools_for_local: bool = False,
        lm_studio_compatibility: bool = True,
        capability_cache_ttl_seconds: int = 300,
        cache: LocalCache | None = None,
        transport=None,
        multimodal: bool = False,
        max_tokens: int | None = None,
        event_callback=None,
    ):
        self.agent_id = agent_id
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.local_model_timeout = local_model_timeout
        self.auto_increase_timeout = auto_increase_timeout
        self.max_retries = max_retries
        self.stream = stream
        self.stream_local_default = stream_local_default
        self.verbose_stream = verbose_stream
        self.tool_calling = tool_calling
        self.supports_tool_calling = supports_tool_calling
        self.allow_native_tools_for_local = allow_native_tools_for_local
        self.lm_studio_compatibility = lm_studio_compatibility
        self.capability_cache_ttl_seconds = capability_cache_ttl_seconds
        self.cache = cache
        self.max_tokens = max_tokens
        self.repo_snapshot_hash = "no-repo"
        self.policy_hash = "no-policy"

        config = {
            "agent_id": agent_id,
            "base_url": base_url,
            "provider": provider,
            "model": model,
            "api_key_env": api_key_env,
            "timeout": timeout,
            "local_model_timeout": local_model_timeout,
            "auto_increase_timeout": auto_increase_timeout,
            "max_retries": max_retries,
            "stream": stream,
            "stream_local_default": stream_local_default,
            "verbose_stream": verbose_stream,
            "tool_calling": tool_calling,
            "supports_tool_calling": supports_tool_calling,
            "allow_native_tools_for_local": allow_native_tools_for_local,
            "lm_studio_compatibility": lm_studio_compatibility,
            "capability_cache_ttl_seconds": capability_cache_ttl_seconds,
            "transport": transport,
            "cache": cache,
            "multimodal": multimodal,
            "max_tokens": max_tokens,
            "event_callback": event_callback,
        }
        # Throws ValueError if provider is unknown
        self._provider_inst = create_code_agent(provider, config)

    def __repr__(self) -> str:
        return repr(self._provider_inst)

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if self.cache and self.cache.allows_llm():
            task = next(
                (
                    str(message.get("content", ""))
                    for message in reversed(messages)
                    if message.get("role") == "user"
                ),
                "",
            )
            cache_key = self.cache.build_llm_key(
                provider=self.provider,
                model=self.model,
                messages=messages,
                task=task,
                repo_snapshot_hash=self.repo_snapshot_hash,
                policy_hash=self.policy_hash,
            )
            cached = self.cache.get_json("llm", cache_key)
            if cached is not None:
                return cached

            response = await self._provider_inst.chat_completion(messages)
            self.cache.set_json("llm", cache_key, response)
            return response
        return await self._provider_inst.chat_completion(messages)

    async def health_check(self) -> dict[str, Any]:
        return await self._provider_inst.health_check()

    async def get_agent_config(self) -> dict[str, Any]:
        if hasattr(self._provider_inst, "get_agent_config"):
            return await self._provider_inst.get_agent_config()
        return {
            "id": self.agent_id,
            "name": f"Agent {self.agent_id}",
            "type": "coding",
            "capabilities": ["code_generation", "file_management", "testing"],
        }

    async def list_agents(self) -> list[dict[str, Any]]:
        if hasattr(self._provider_inst, "list_agents"):
            return await self._provider_inst.list_agents()
        return [{"id": self.agent_id, "name": f"Agent {self.agent_id}", "status": "active"}]

    def _build_headers(self) -> dict[str, str]:
        if hasattr(self._provider_inst, "_build_headers"):
            return self._provider_inst._build_headers()
        return {}

    def _sanitize_log_headers(self, headers: dict) -> dict:
        if hasattr(self._provider_inst, "_sanitize_log_headers"):
            return self._provider_inst._sanitize_log_headers(headers)
        from .sanitizer import Sanitizer
        return Sanitizer.sanitize_data(headers)

    def set_cache_context(self, repo_snapshot_hash: str, policy_hash: str) -> None:
        self.repo_snapshot_hash = repo_snapshot_hash
        self.policy_hash = policy_hash
