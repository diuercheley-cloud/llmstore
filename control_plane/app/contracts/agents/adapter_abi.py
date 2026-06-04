import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    @abstractmethod
    async def manifest(self) -> AdapterManifest:
        """Returns the adapter manifest and capability declarations."""
        pass

    @abstractmethod
    async def schema(self) -> Dict[str, Any]:
        """Returns the JSON schema for configuration and execution parameters."""
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Verifies if the adapter and its dependencies are operational."""
        pass

    @abstractmethod
    async def dry_run(self, params: Dict[str, Any]) -> tuple[bool, str]:
        """Validates parameters without executing the core logic."""
        pass


class ToolAdapterV1(AdapterABI):
    @abstractmethod
    async def execute(self, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the tool logic with the given input and context."""
        pass


class MemoryProviderV1(AdapterABI):
    @abstractmethod
    async def store(self, agent_id: uuid.UUID, run_id: uuid.UUID, item: Dict[str, Any]) -> bool:
        """Persists a memory item."""
        pass

    @abstractmethod
    async def retrieve(self, agent_id: uuid.UUID, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves relevant memory items."""
        pass


class EvalProviderV1(AdapterABI):
    @abstractmethod
    async def evaluate(self, run_id: uuid.UUID, criteria: List[str]) -> Dict[str, Any]:
        """Evaluates an agent run against specified criteria."""
        pass


class PlannerProviderV1(AdapterABI):
    @abstractmethod
    async def plan(self, goal: str, available_tools: List[str], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a plan (sequence of tasks) for the given goal."""
        pass
