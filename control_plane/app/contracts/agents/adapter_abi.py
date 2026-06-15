import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AdapterManifest(BaseModel):
    id: str
    name: str
    version: str
    compatibility_version: str = "v1"
    description: str | None = None
    author: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)


class AdapterABI(ABC):
    @abstractmethod
    async def manifest(self) -> AdapterManifest:
        """Returns the adapter manifest and capability declarations."""
        pass

    @abstractmethod
    async def schema(self) -> dict[str, Any]:
        """Returns the JSON schema for configuration and execution parameters."""
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Verifies if the adapter and its dependencies are operational."""
        pass

    @abstractmethod
    async def dry_run(self, params: dict[str, Any]) -> tuple[bool, str]:
        """Validates parameters without executing the core logic."""
        pass


class ToolAdapterV1(AdapterABI):
    @abstractmethod
    async def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Executes the tool logic with the given input and context."""
        pass


class MemoryProviderV1(AdapterABI):
    @abstractmethod
    async def store(self, agent_id: uuid.UUID, run_id: uuid.UUID, item: dict[str, Any]) -> bool:
        """Persists a memory item."""
        pass

    @abstractmethod
    async def retrieve(
        self, agent_id: uuid.UUID, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Retrieves relevant memory items."""
        pass


class EvalProviderV1(AdapterABI):
    @abstractmethod
    async def evaluate(self, run_id: uuid.UUID, criteria: list[str]) -> dict[str, Any]:
        """Evaluates an agent run against specified criteria."""
        pass


class PlannerProviderV1(AdapterABI):
    @abstractmethod
    async def plan(
        self, goal: str, available_tools: list[str], history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generates a plan (sequence of tasks) for the given goal."""
        pass
