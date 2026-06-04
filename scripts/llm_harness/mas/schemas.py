from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    role: str
    model_profile: Optional[str] = None
    description: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    prompt: str

class AgentCapability(BaseModel):
    name: str
    description: str

class AgentGoal(BaseModel):
    description: str
    priority: int = 1
    status: Literal["pending", "achieved", "failed"] = "pending"

class AgentPolicy(BaseModel):
    approval_policy: Optional[str] = "manual"
    max_steps: int = 10
    forbidden_tools: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)

class AgentRole(BaseModel):
    name: str
    description: str
    responsibilities: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)

class TeamMember(BaseModel):
    agent_id: str
    role: str
    model_profile: Optional[str] = None
    fallback_model_profile: Optional[str] = None

TeamTopology = Literal["linear", "supervisor", "mesh", "hierarchical"]

class AgentTeam(BaseModel):
    name: str
    description: str
    members: List[TeamMember]
    topology: TeamTopology = "supervisor"
    shared_blackboard: bool = True
    default_model_profile: Optional[str] = None
    approval_policy: Optional[str] = "manual"

class TeamRunResult(BaseModel):
    team_name: str
    success: bool
    message: str
    steps: int
    outputs: Dict[str, Any] = Field(default_factory=dict)

class AgentMessage(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: str
    recipient: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SubTask(BaseModel):
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: Optional[str] = None

class BlackboardState(BaseModel):
    task: str
    plan: List[Dict[str, Any]] = Field(default_factory=list)
    sub_tasks: List[SubTask] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    reviewer_feedback: List[str] = Field(default_factory=list)
    messages: List[AgentMessage] = Field(default_factory=list)
    custom_state: Dict[str, Any] = Field(default_factory=dict)
