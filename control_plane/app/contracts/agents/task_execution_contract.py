import uuid
from typing import Any, Dict, Optional

from app.contracts.agents.base import AgentContract, CompatibilityPolicy
from pydantic import BaseModel, Field


class ModelReasoningTaskInputV1(BaseModel):
    prompt: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)


class ToolCallTaskInputV1(BaseModel):
    tool_name: str = Field(min_length=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MemoryReadTaskInputV1(BaseModel):
    memory_type: str = Field(default="short_term", min_length=1)
    collection_id: Optional[uuid.UUID] = None
    limit: int = Field(default=10, ge=1, le=100)


class MemoryWriteTaskInputV1(BaseModel):
    memory_type: str = Field(default="short_term", min_length=1)
    content: str = Field(min_length=1)
    user_id: Optional[str] = None
    summary: Optional[str] = None
    collection_id: Optional[uuid.UUID] = None


class ApprovalWaitTaskInputV1(BaseModel):
    tool_name: str = Field(min_length=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None
    risk_level: Optional[str] = None
    required_role: Optional[str] = None


class HandoffTaskInputV1(BaseModel):
    target_agent_id: uuid.UUID
    reason: str = Field(min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)


class WorkflowSignalTaskInputV1(BaseModel):
    workflow_run_id: uuid.UUID
    signal_name: str = Field(min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class FinalResponseTaskInputV1(BaseModel):
    output: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskExecutionResultV1(BaseModel):
    execution_mode: str
    executor_name: str
    result: Dict[str, Any] = Field(default_factory=dict)


class ModelReasoningTaskContractV1(AgentContract[ModelReasoningTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_model_reasoning"
    version = "1.0.0"
    input_schema = ModelReasoningTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class ToolCallTaskContractV1(AgentContract[ToolCallTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_tool_call"
    version = "1.0.0"
    input_schema = ToolCallTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class MemoryReadTaskContractV1(AgentContract[MemoryReadTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_memory_read"
    version = "1.0.0"
    input_schema = MemoryReadTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class MemoryWriteTaskContractV1(AgentContract[MemoryWriteTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_memory_write"
    version = "1.0.0"
    input_schema = MemoryWriteTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class ApprovalWaitTaskContractV1(AgentContract[ApprovalWaitTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_approval_wait"
    version = "1.0.0"
    input_schema = ApprovalWaitTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class HandoffTaskContractV1(AgentContract[HandoffTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_handoff"
    version = "1.0.0"
    input_schema = HandoffTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class WorkflowSignalTaskContractV1(AgentContract[WorkflowSignalTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_workflow_signal"
    version = "1.0.0"
    input_schema = WorkflowSignalTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD


class FinalResponseTaskContractV1(AgentContract[FinalResponseTaskInputV1, TaskExecutionResultV1]):
    contract_name = "agent_task_final_response"
    version = "1.0.0"
    input_schema = FinalResponseTaskInputV1
    output_schema = TaskExecutionResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
