import uuid

import pytest
from app.contracts.agents.memory_injection_contract import MemoryInjectionContractV1
from app.contracts.agents.planner_contract import AgentPlanV1, PlannerContractV1
from app.contracts.agents.runtime_contract import (
    AgentRunRequestV1,
    RuntimeContractV1,
)
from app.contracts.agents.tool_call_contract import AgentToolResultV1, ToolCallContractV1
from app.contracts.base import ContractValidationError


def test_runtime_contract_validation():
    valid_request = {
        "agent_id": str(uuid.uuid4()),
        "tenant_id": "tenant-1",
        "input_text": "Hello world",
    }
    obj = RuntimeContractV1.validate_input(valid_request)
    assert isinstance(obj, AgentRunRequestV1)

    invalid_request = {"agent_id": "not-a-uuid"}
    with pytest.raises(ContractValidationError):
        RuntimeContractV1.validate_input(invalid_request)


def test_planner_contract_output_validation():
    valid_plan = {
        "plan_id": str(uuid.uuid4()),
        "goal": "Test goal",
        "tasks": [{"task_id": "t1", "description": "task 1"}],
    }
    obj = PlannerContractV1.validate_output(valid_plan)
    assert isinstance(obj, AgentPlanV1)
    assert len(obj.tasks) == 1

    invalid_plan = {"goal": "missing plan_id"}
    with pytest.raises(ContractValidationError):
        PlannerContractV1.validate_output(invalid_plan)


def test_tool_call_contract_validation():
    valid_result = {"status": "success", "output": {"data": 42}, "latency_ms": 150}
    obj = ToolCallContractV1.validate_output(valid_result)
    assert isinstance(obj, AgentToolResultV1)
    assert obj.status == "success"


def test_memory_injection_contract_validation():
    valid_context = {
        "context_block": "Relevant info",
        "citations": [
            {
                "memory_id": str(uuid.uuid4()),
                "content_snippet": "snippet",
                "source": "doc1",
                "relevance_score": 0.95,
            }
        ],
    }
    MemoryInjectionContractV1.validate_output(valid_context)


def test_backward_compatibility_policy():
    # Adding extra fields should be allowed by Pydantic default (BACKWARD compatibility)
    valid_request_extra = {
        "agent_id": str(uuid.uuid4()),
        "tenant_id": "t1",
        "input_text": "text",
        "future_field": "ignore me",
    }
    # Pydantic by default ignores extra fields if not configured otherwise
    obj = RuntimeContractV1.validate_input(valid_request_extra)
    assert not hasattr(obj, "future_field")
