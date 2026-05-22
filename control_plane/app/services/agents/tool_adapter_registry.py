import logging
from typing import Dict, List, Optional, Type
from app.services.agents.tool_adapter_contract import ToolAdapterContract

logger = logging.getLogger(__name__)

class ToolAdapterRegistry:
    """
    Registry for executable ToolAdapters.
    This is a singleton that holds instances of ToolAdapterContract.
    """
    _instance = None
    _adapters: Dict[str, ToolAdapterContract] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolAdapterRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, adapter: ToolAdapterContract) -> None:
        """Registers a tool adapter. Enforces version and schema requirements."""
        if not adapter.name:
            raise ValueError("Adapter must have a name.")
        if not adapter.version:
            raise ValueError(f"Adapter '{adapter.name}' must have a version.")
        if not adapter.input_schema or not adapter.output_schema:
            raise ValueError(f"Adapter '{adapter.name}' must have input and output schemas.")

        logger.info(f"Registering tool adapter: {adapter.name} (v{adapter.version})")
        self._adapters[adapter.name] = adapter

    def get_adapter(self, name: str) -> Optional[ToolAdapterContract]:
        """Retrieves a registered adapter by name."""
        return self._adapters.get(name)

    def list_adapters(self) -> List[ToolAdapterContract]:
        """Lists all registered adapters."""
        return list(self._adapters.values())

    def clear(self) -> None:
        """Clears all registered adapters (primarily for testing)."""
        self._adapters.clear()

# Global singleton instance
adapter_registry = ToolAdapterRegistry()
