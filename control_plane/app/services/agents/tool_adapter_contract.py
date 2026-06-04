# Owner: agent-platform
import abc
from typing import Any, Dict


class ToolAdapterContract(abc.ABC):
    """
    Contract for real, versioned and executable tool adapters.
    All real tools must implement this interface to be registered in the agentic runtime.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The canonical name of the tool."""
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Semantic version of the tool adapter."""
        pass

    @property
    @abc.abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema for the tool input."""
        pass

    @property
    @abc.abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """JSON Schema for the tool output."""
        pass

    @property
    @abc.abstractmethod
    def side_effect_level(self) -> str:
        """One of: none, read, write, destructive, external."""
        pass

    @abc.abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Performs the real execution of the tool.
        Must respect security boundaries and tenant isolation.
        """
        pass

    @abc.abstractmethod
    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        """
        Simulates execution without side effects.
        Mandatory for write/destructive tools.
        """
        pass

    @abc.abstractmethod
    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        """
        Attempts to revert side effects produced by a previous execution.
        """
        pass

    @abc.abstractmethod
    async def healthcheck(self) -> bool:
        """Verifies if the tool's dependencies are available."""
        pass

    def to_registry_dict(self) -> Dict[str, Any]:
        """Converts the adapter metadata to a format suitable for ToolRegistry."""
        return {
            "name": self.name,
            "version": self.version,
            "input_schema_json": self.input_schema,
            "output_schema_json": self.output_schema,
            "side_effect_level": self.side_effect_level,
            "rollback_supported": True, # Adapters should ideally support rollback
        }
