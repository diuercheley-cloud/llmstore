import uuid
from typing import Any

from app.contracts.agents.base import AgentContract, CompatibilityPolicy
from pydantic import BaseModel, Field


class AgentTaskV1(BaseModel):
    task_id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentPlanV1(BaseModel):
    plan_id: uuid.UUID
    goal: str
    tasks: list[AgentTaskV1]
    requires_approval: bool = False


class PlannerContractV1(AgentContract[BaseModel, AgentPlanV1]):
    contract_name = "agent_planner"
    version = "1.0.0"
    input_schema = BaseModel  # Planner usually takes internal context
    output_schema = AgentPlanV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
