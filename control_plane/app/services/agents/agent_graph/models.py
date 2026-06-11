from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentNodeType(str, Enum):
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    CREW = "crew"
    HIERARCHICAL = "hierarchical"


class GraphExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class AgentNode:
    id: str
    type: AgentNodeType
    agent_id: uuid.UUID | None = None
    name: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    input: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: int = 300


@dataclass
class GraphEdge:
    source: str
    target: str
    condition: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentGraphSpec:
    nodes: list[AgentNode]
    edges: list[GraphEdge]
    name: str = ""
    description: str = ""
    max_concurrency: int = 5
    enable_checkpointing: bool = True


@dataclass
class NodeExecutionResult:
    node_id: str
    status: NodeExecutionStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    retry_attempts: int = 0
    checkpoint: dict[str, Any] | None = None


@dataclass
class GraphExecutionResult:
    run_id: str
    status: GraphExecutionStatus
    node_results: dict[str, NodeExecutionResult] = field(default_factory=dict)
    error: str | None = None
    started_at: str = ""
    completed_at: str = ""
    checkpoint_dir: str = ""
