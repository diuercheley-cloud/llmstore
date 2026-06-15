import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agent_studio import AgentFlowVersion
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_validator import FlowValidator


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_flow_validation_detects_high_risk_missing_approval():
    graph = {
        "nodes": [
            {
                "id": "n1",
                "node_type": "tool_call",
                "config": {"tool_name": "delete_database", "requires_approval": False},
            },
            {"id": "n2", "node_type": "final_response"},
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    }

    version = AgentFlowVersion(
        id=uuid.uuid4(), flow_id=uuid.uuid4(), version_label="v1", graph_json=graph
    )

    validator = FlowValidator()
    errors = validator.validate(version)

    # Now that we have a terminal node, only the missing_approval error should remain.
    assert len(errors) == 1
    assert errors[0]["code"] == "missing_approval"


@pytest.mark.asyncio
async def test_flow_compilation_generates_tasks():
    graph = {
        "nodes": [
            {"id": "node1", "node_type": "agent", "label": "Thinker"},
            {"id": "node2", "node_type": "tool_call", "config": {"tool_name": "search"}},
        ]
    }

    version = AgentFlowVersion(
        id=uuid.uuid4(), flow_id=uuid.uuid4(), version_label="v1", graph_json=graph
    )

    compiler = FlowCompiler()
    plan = compiler.compile(version)

    assert len(plan["tasks"]) == 2
    assert plan["tasks"][0]["task_type"] == "model_reasoning"
    assert plan["tasks"][1]["task_type"] == "tool_call"


import pytest_asyncio
