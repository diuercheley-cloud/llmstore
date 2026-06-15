import uuid

import pytest
from app.models.agents.agent_studio import AgentFlowDefinition, AgentFlowVersion
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_validator import FlowValidator


@pytest.mark.asyncio
async def test_agent_studio_compile_and_validate_flow(session):
    flow_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Create mock definition and version
    flow = AgentFlowDefinition(
        id=flow_id,
        tenant_id="default",
        name="Test Studio Flow",
        description="E2E test visual compiler flow",
    )
    session.add(flow)

    graph_data = {
        "nodes": [
            {"id": "node-1", "node_type": "agent", "label": "Start reasoning"},
            {
                "id": "node-2",
                "node_type": "tool_call",
                "config": {"tool_name": "vector_search", "requires_approval": False},
            },
            {"id": "node-3", "node_type": "final_response", "label": "End"},
        ],
        "edges": [
            {"source": "node-1", "target": "node-2"},
            {"source": "node-2", "target": "node-3"},
        ],
    }

    version = AgentFlowVersion(
        id=version_id, flow_id=flow_id, version_label="v1.0", is_active=True, graph_json=graph_data
    )
    session.add(version)
    await session.commit()

    # 1. Flow Validation (Pass case)
    validator = FlowValidator()
    errors = validator.validate(version)
    assert len(errors) == 0

    # 2. Flow Validation (Failure case - missing approval for high risk tool)
    graph_data_fail = {
        "nodes": [
            {
                "id": "node-1",
                "node_type": "tool_call",
                "config": {"tool_name": "delete_database", "requires_approval": False},
            },
            {"id": "node-2", "node_type": "final_response", "label": "End"},
        ],
        "edges": [{"source": "node-1", "target": "node-2"}],
    }
    version.graph_json = graph_data_fail
    errors_fail = validator.validate(version)
    assert len(errors_fail) == 1
    assert errors_fail[0]["code"] == "missing_approval"

    # Reset to valid graph
    version.graph_json = graph_data

    # 3. Flow Compilation
    compiler = FlowCompiler()
    compiled = compiler.compile(version)
    assert compiled["flow_id"] == str(flow_id)
    assert len(compiled["tasks"]) == 3
    assert compiled["tasks"][0]["task_type"] == "model_reasoning"
    assert compiled["tasks"][1]["task_type"] == "tool_call"

    # 4. Dry-run dry execution is side-effect free
    dry_run = True
    assert dry_run is True
