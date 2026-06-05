import logging
from typing import List, Optional, Tuple

from app.services.sandbox.base import (
    SandboxProvider, 
    SandboxLevel, 
    SandboxPolicy, 
    SandboxExecutionRequest, 
    SandboxExecutionResult
)
from app.services.sandbox.providers.noop_provider import (
    NoopSandboxProvider, 
    WasiSandboxProvider, 
    GVisorSandboxProvider, 
    FirecrackerSandboxProvider
)

logger = logging.getLogger(__name__)


class SandboxService:
    def __init__(self):
        self.providers: List[SandboxProvider] = [
            NoopSandboxProvider(),
            WasiSandboxProvider(),
            GVisorSandboxProvider(),
            FirecrackerSandboxProvider()
        ]

    async def execute_tool_safely(
        self, 
        tool_name: str, 
        command: List[str], 
        requested_level: SandboxLevel = SandboxLevel.NONE
    ) -> SandboxExecutionResult:
        # 1. Define Policy for Tool
        policy = self._get_policy_for_tool(tool_name, requested_level)
        
        # 2. Select Provider
        provider = self._select_provider(policy.required_level)
        
        if not provider:
            return SandboxExecutionResult(
                status="blocked", 
                reason=f"No provider available for sandbox level {policy.required_level}",
                provider_name="none"
            )

        # 3. Create Request
        request = SandboxExecutionRequest(
            command=command,
            policy=policy
        )

        # 4. Execute
        return await provider.execute(request)

    def _get_policy_for_tool(self, tool_name: str, requested_level: SandboxLevel) -> SandboxPolicy:
        """
        Determines the policy for a given tool.
        Dangerous tools (filesystem, shell) automatically require higher sandbox levels.
        """
        dangerous_tools = {"shell_execute", "file_write", "network_proxy", "python_repl"}
        
        level = requested_level
        if tool_name in dangerous_tools and level == SandboxLevel.NONE:
            level = SandboxLevel.WASI # Minimum safe level for dangerous tools

        return SandboxPolicy(
            required_level=level,
            allow_network=False if tool_name != "network_proxy" else True,
            allow_filesystem=False if "file" not in tool_name else True,
            timeout_seconds=30,
            memory_limit_mb=128
        )

    def _select_provider(self, required_level: SandboxLevel) -> Optional[SandboxProvider]:
        # Filter available providers that meet or exceed the required level
        # For simplicity, we pick the first available that matches exactly or is higher
        for p in self.providers:
            if p.get_level() == required_level and p.is_available():
                return p
        
        # Fallback to noop if none is strictly required (level NONE)
        if required_level == SandboxLevel.NONE:
            return next((p for p in self.providers if isinstance(p, NoopSandboxProvider)), None)
            
        return None

    def list_providers(self) -> List[dict]:
        return [
            {
                "name": p.__class__.__name__,
                "level": p.get_level().value,
                "is_available": p.is_available()
            }
            for p in self.providers
        ]
