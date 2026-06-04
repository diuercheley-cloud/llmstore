import uuid
from typing import Any, Dict, List

from app.contracts.agents.base import AgentContract, CompatibilityPolicy
from pydantic import BaseModel, Field


class AgentTaskV1(BaseModel):
    task_id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentPlanV1(BaseModel):
    plan_id: uuid.UUID
    goal: str
    tasks: List[AgentTaskV1]
    requires_approval: bool = False

class PlannerContractV1(AgentContract[BaseModel, AgentPlanV1]):
    contract_name = "agent_planner"
    version = "1.0.0"
    input_schema = BaseModel # Planner usually takes internal context
    output_schema = AgentPlanV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
