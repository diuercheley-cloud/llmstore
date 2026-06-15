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
    description: str


class AgentGoal(BaseModel):
    description: str
    priority: int = 1
    status: Literal["pending", "achieved", "failed"] = "pending"


class AgentPolicy(BaseModel):
    approval_policy: str | None = "manual"
    max_steps: int = 10
    forbidden_tools: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)


class AgentRole(BaseModel):
    name: str
    description: str
    responsibilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)


class TeamMember(BaseModel):
    agent_id: str
    role: str
    model_profile: str | None = None
    fallback_model_profile: str | None = None


TeamTopology = Literal["linear", "supervisor", "mesh", "hierarchical"]


class AgentTeam(BaseModel):
    name: str
    description: str
    members: list[TeamMember]
    topology: TeamTopology = "supervisor"
    shared_blackboard: bool = True
    default_model_profile: str | None = None
    approval_policy: str | None = "manual"


class TeamRunResult(BaseModel):
    team_name: str
    success: bool
    message: str
    steps: int
    outputs: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: str
    recipient: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


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
