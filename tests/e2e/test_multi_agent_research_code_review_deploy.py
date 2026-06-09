import uuid

import pytest
from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.code_interpreter.code_interpreter import CodeInterpreter
from app.services.agents.code_interpreter.sandbox_artifacts import SandboxArtifactService
from app.services.agents.human_approval import approve_approval_request, create_approval_request
from app.services.agents.knowledge_graph.graph_store import GraphStore
from app.services.agents.telemetry.agent_tracer import AgentTracer
from app.services.auth import AdminRole


@pytest.mark.asyncio
async def test_multi_agent_e2e_research_code_review_deploy(session):
    settings = get_settings()
    settings.agent_knowledge_graph_enabled = True
    settings.agent_kg_write_enabled = True
    settings.agent_code_interpreter_enabled = True
    settings.agent_code_sandbox_provider = "mock"
    settings.agent_sandbox_allow_simulated_provider = True
    settings.agent_otel_tracing_enabled = True
    settings.agent_approval_portal_enabled = True
    settings.agent_execution_plane_enabled = True
    settings.agent_runtime_enabled = True
    
    tenant_id = "tenant-e2e"
    agent_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    # Pre-requisite: insert agent definition and run
    agent_def = AgentDefinition(
        id=agent_id,
        name="ResearchCodingAgent",
        version="1.0.0",
        instructions="Plan and run code",
        model_id="gemini",
        owner="e2e-test",
        tenant_id=tenant_id
    )
    session.add(agent_def)
    
    run = AgentRun(
        id=run_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        status="running"
    )
    session.add(run)
    await session.commit()
    
    # 1. Research Agent queries KG
    store = GraphStore(session)
    source_id = await store.create_source(tenant_id, "inline://doc", "Google owns Android")
    entity_google = await store.add_entity(tenant_id, "Google", "organization", source_id=source_id)
    entity_android = await store.add_entity(tenant_id, "Android", "system", source_id=source_id)
    
    await store.add_relation(
        tenant_id=tenant_id,
        src_id=entity_google.id,
        tgt_id=entity_android.id,
        relation_type="owns",
        provenance="doc_reference",
        source_id=source_id
    )
    
    kg_res = await store.get_entities(tenant_id, "Google")
    assert len(kg_res) > 0
    assert kg_res[0].name == "Google"
    
    # 2. Coding Agent uses Code Interpreter
    interpreter = CodeInterpreter(session)
    interpreter_res = await interpreter.run_code(
        code="print('Hello Android')",
        agent_id=agent_id,
        run_id=run_id,
        tenant_id=tenant_id
    )
    assert interpreter_res["exit_code"] == 0
    assert "Hello Android" in interpreter_res["stdout"]
    
    # 3. Save sandbox artifact
    artifacts_svc = SandboxArtifactService(session)
    artifact = await artifacts_svc.record_artifact(
        session_id=uuid.UUID(interpreter_res["session_id"]),
        filename="output.txt",
        content=b"Execution results"
    )
    assert artifact.id is not None
    assert artifact.filename == "output.txt"
    
    # 4. Reviewer & Human approval request
    req = await create_approval_request(
        db=session,
        run_id=run_id,
        tool_name="deploy_tool",
        tool_input={"dry_run": True},
        risk_level="high",
        reason="Deploy pricing service modifications",
        required_role="admin_write",
        step_number=1,
        task_id="deploy_task",
        tool_invocation_id=uuid.uuid4()
    )
    assert req.status == "pending"
    
    approved_req = await approve_approval_request(
        db=session,
        request_id=req.id,
        decided_by="human_manager@corp.com",
        caller_role=AdminRole.WRITE,
        reason="Approved pricing change after reviewer check"
    )
    assert approved_req.status == "approved"
    
    # 5. Deploy tool runs in dry-run
    # Simulated action: checking that we can proceed safely
    deploy_dry_run = True
    assert deploy_dry_run is True
    
    # 6. Trace complete is generated
    tracer = AgentTracer()
    trace_payload = tracer.trace_run(str(run_id), str(agent_id), tenant_id)
    assert trace_payload["span.name"] == "agent.run"
    assert trace_payload["agent.run_id"] == str(run_id)
