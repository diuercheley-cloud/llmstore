from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    role: str
    model_profile: str | None = None
    description: str | None = None
    tools: list[str] = Field(default_factory=list)
    prompt: str


class AgentCapability(BaseModel):
    name: str
    version: str
    description: str


class TeamMember(BaseModel):
    agent_id: str
    role: str
    model_profile: str | None = None
    permissions: list[str] = Field(default_factory=list)


TeamTopology = Literal[
    "linear",
    "supervisor",
    "hierarchical",
    "debate",
    "planner_coder_reviewer",
    "sequential",
    "parallel_dry_run",
]


class AgentTeam(BaseModel):
    team_name: str
    description: str
    members: list[TeamMember]
    topology: TeamTopology = "supervisor"
    shared_blackboard: bool = True
    communication_contracts: dict[str, Any] = Field(default_factory=dict)
    escalation_policy: str | None = None
    max_iterations: int = 10
    stop_conditions: list[str] = Field(default_factory=list)
    approval_policy: str | None = "manual"


class AgentMessage(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: str
    recipient: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    hash: str | None = None


class SubTask(BaseModel):
    id: str
    description: str
    assigned_to: str | None = None
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: str | None = None


class BlackboardState(BaseModel):
    task: str
    plan: list[dict[str, Any]] = Field(default_factory=list)
    sub_tasks: list[SubTask] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    test_results: dict[str, Any] = Field(default_factory=dict)
    reviewer_feedback: list[str] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    custom_state: dict[str, Any] = Field(default_factory=dict)
