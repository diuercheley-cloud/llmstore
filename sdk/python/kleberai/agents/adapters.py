import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class AdapterManifest(BaseModel):
    id: str
    name: str
    version: str
    compatibility_version: str = "v1"
    description: Optional[str] = None
    author: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)


class AdapterABI(ABC):
    """Stable ABI for all Agentic Adapters."""

    @abstractmethod
    async def manifest(self) -> AdapterManifest:
        """Returns the adapter manifest."""
        pass

    @abstractmethod
    async def schema(self) -> Dict[str, Any]:
        """Returns the JSON schema for configuration and execution."""
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Returns True if the adapter is healthy."""
        pass

    @abstractmethod
    async def dry_run(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates parameters without executing."""
        pass


class ToolAdapterV1(AdapterABI):
    """Stable ABI for Tool Adapters."""

    @abstractmethod
    async def execute(self, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the tool logic."""
        pass


class MemoryProviderV1(AdapterABI):
    """Stable ABI for Memory Providers."""

    @abstractmethod
    async def store(self, agent_id: uuid.UUID, run_id: uuid.UUID, item: Dict[str, Any]) -> bool:
        """Stores a memory item."""
        pass

    @abstractmethod
    async def retrieve(
        self, agent_id: uuid.UUID, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves memory items."""
        pass


class EvalProviderV1(AdapterABI):
    """Stable ABI for Evaluation Providers."""

    @abstractmethod
    async def evaluate(self, run_id: uuid.UUID, criteria: List[str]) -> Dict[str, Any]:
        """Evaluates an agent run."""
        pass


class PlannerProviderV1(AdapterABI):
    """Stable ABI for Planners."""

    @abstractmethod
    async def plan(
        self, goal: str, available_tools: List[str], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates an execution plan."""
        pass
