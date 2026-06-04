from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

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
