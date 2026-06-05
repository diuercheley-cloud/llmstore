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
    version: str
    description: str

class TeamMember(BaseModel):
    agent_id: str
    role: str
    model_profile: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

TeamTopology = Literal[
    "linear", 
    "supervisor", 
    "hierarchical", 
    "debate", 
    "planner_coder_reviewer",
    "sequential",
    "parallel_dry_run"
]

class AgentTeam(BaseModel):
    team_name: str
    description: str
    members: List[TeamMember]
    topology: TeamTopology = "supervisor"
    shared_blackboard: bool = True
    communication_contracts: Dict[str, Any] = Field(default_factory=dict)
    escalation_policy: Optional[str] = None
    max_iterations: int = 10
    stop_conditions: List[str] = Field(default_factory=list)
    approval_policy: Optional[str] = "manual"

class AgentMessage(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: str
    recipient: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    hash: Optional[str] = None

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
