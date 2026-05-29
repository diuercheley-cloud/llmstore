import pytest
import uuid
from app.services.agents.studio.flow_versioning import FlowVersioningService
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_runtime_adapter import FlowRuntimeAdapter
from app.models.agent_studio import AgentFlowVersion

@pytest.fixture
async def setup_flow(session):
    service = FlowVersioningService(session)
    flow = await service.create_flow("tenant_a", "Test Flow", "Description")
    return flow

@pytest.mark.asyncio
async def test_flow_valido_salva(session, setup_flow):
    service = FlowVersioningService(session)
    graph = {
        "nodes": [{"id": "n1", "node_type": "agent", "label": "Main Agent"}, {"id": "n2", "node_type": "final_response"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}]
    }
    version = await service.save_version(setup_flow.id, graph, "v1", make_active=True)
    assert version.version_label == "v1"
    assert len(version.nodes) == 2
    assert len(version.edges) == 1

@pytest.mark.asyncio
async def test_ciclo_bloqueado(session, setup_flow):
    service = FlowVersioningService(session)
    validator = FlowValidator()
    
    # Loop: n1 -> n2 -> n1
    graph = {
        "nodes": [{"id": "n1", "node_type": "agent"}, {"id": "n2", "node_type": "agent"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}, {"id": "e2", "source": "n2", "target": "n1"}]
    }
    version = await service.save_version(setup_flow.id, graph, "v_cyclic")
    errors = validator.validate(version)
    assert any(e["code"] == "cyclic_graph" for e in errors)

@pytest.mark.asyncio
async def test_node_high_risk_exige_approval(session, setup_flow):
    service = FlowVersioningService(session)
    validator = FlowValidator()
    
    graph = {
        "nodes": [
            {"id": "n1", "node_type": "tool_call", "config": {"tool_name": "delete_database", "requires_approval": False}},
            {"id": "n2", "node_type": "final_response"}
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}]
    }
    version = await service.save_version(setup_flow.id, graph, "v_risky")
    errors = validator.validate(version)
    assert any(e["code"] == "missing_approval" for e in errors)

@pytest.mark.asyncio
async def test_compile_gera_agent_plan(session, setup_flow):
    service = FlowVersioningService(session)
    compiler = FlowCompiler()
    
    graph = {
        "nodes": [{"id": "n1", "node_type": "agent"}, {"id": "n2", "node_type": "final_response"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}]
    }
    version = await service.save_version(setup_flow.id, graph, "v_compile")
    plan = compiler.compile(version)
    
    assert len(plan["tasks"]) == 2
    assert plan["tasks"][1]["dependencies"] == [plan["tasks"][0]["id"]]

@pytest.mark.asyncio
async def test_dry_run_nao_executa_tool_real(session, setup_flow):
    service = FlowVersioningService(session)
    adapter = FlowRuntimeAdapter(session)
    
    graph = {
        "nodes": [{"id": "n1", "node_type": "agent"}, {"id": "n2", "node_type": "final_response"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}]
    }
    version = await service.save_version(setup_flow.id, graph, "v_dryrun")
    await session.commit()
    
    res = await adapter.dry_run(version.id, {"input": "test"})
    assert res["status"] == "success"
    assert any("Simulated" in event["message"] for event in res["trace"])

@pytest.mark.asyncio
async def test_versionamento_funciona(session, setup_flow):
    service = FlowVersioningService(session)
    graph = {"nodes": [], "edges": []}
    
    v1 = await service.save_version(setup_flow.id, graph, "1.0.0", make_active=True)
    v2 = await service.save_version(setup_flow.id, graph, "1.1.0", make_active=True)
    
    assert v2.is_active is True
    # Re-fetch v1 to check if it's inactive
    await session.refresh(v1)
    assert v1.is_active is False
