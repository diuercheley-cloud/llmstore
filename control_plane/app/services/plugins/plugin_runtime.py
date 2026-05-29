"""Plugin runtime entrypoint for governed execution."""

# Owner: platform-ops
"""Plugin runtime entrypoint for governed execution."""

# Owner: platform-ops
import uuid
import logging
from app.core.config import get_settings
from app.services.agents.tool_sandbox import execute_in_sandbox

logger = logging.getLogger(__name__)

class PluginRuntimeService:
    def __init__(self, db):
        self.db = db
        self.settings = get_settings()

    async def run_plugin(self, plugin_id: uuid.UUID, code: str, parameters: dict):
        if not self.settings.plugin_runtime_enabled:
             raise RuntimeError("Plugin runtime is disabled")
        
        # In real implementation, we would load the plugin code from disk/registry
        # and check its manifest and sandbox policy.
        
        return await execute_in_sandbox(
            db=self.db,
            tenant_id="plugin-runtime", # placeholder
            invocation_id=uuid.uuid4(),
            tool_name=f"plugin-{plugin_id}",
            tool_category="plugin",
            parameters=parameters,
            allowed_commands=["*"], # Should be restricted by manifest
            timeout_seconds=30,
            sandbox_type=self.settings.agent_code_sandbox_provider
        )
