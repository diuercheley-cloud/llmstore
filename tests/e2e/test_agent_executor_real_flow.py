import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.config import get_settings
from app.services.agents.agent_worker import AgentWorkerService
from app.services.agents.tool_adapters import register_all_adapters
from app.services.agents.agent_llm_provider import MockAgentLLMProvider, ProviderResponse, LLMProviderType
from app.services.agents.human_approval import approve_approval_request
from app.services.auth import AdminRole
from app.core.time import utc_now


class ExplicitMockLLMProvider(MockAgentLLMProvider):
    def __init__(self, responses):
        super().__init__(responses)
        self.responses = responses
        self.current_idx = 0
        self._provider_type = LLMProviderType.MOCK

    async def generate(self, agent_def, run, allowed_tools, input_override=None):
        if self.current_idx < len(self.responses):
            res = self.responses[self.current_idx]
            self.current_idx += 1
        else:
            res = {
                "type": "final",
                "output": "Fallback final answer",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "cost_brl": 0.00075
            }

        usage = res.get("usage", {"prompt_tokens": 10, "completion_tokens": 5})
        resp = ProviderResponse(
            type=res.get("type", "final"),
            output=res.get("output", ""),
            usage=usage,
            cost_brl=res.get("cost_brl", 0.0),
            provider_type=LLMProviderType.MOCK.value,
            model_id=agent_def.model_id if agent_def else "mock-model",
            execution_mode="development",
            tokens={"prompt": usage.get("prompt_tokens", 0), "completion": usage.get("completion_tokens", 0)},
            latency=5.0,
            fallback_used=False,
            validation_status="mock_bypass",
            tool_name=res.get("tool_name"),
            tool_input=res.get("tool_input"),
        )
        for k, v in res.items():
            if k not in resp:
                resp[k] = v
        return resp


@pytest.mark.asyncio
async def test_agent_executor_real_flow(e2e_client, monkeypatch):
    """
    E2E Test to validate the complete agent executor lifecycle flow.
    Ensures that AgentRuntime, AgentExecutor, AgentQueue, AgentWorker,
    ToolExecutor, Memory retention, HITL Approvals, Receipts generation,
    and Observability traces operate end-to-end without silent mocks.
    """
    # 1. Ensure the background AgentWorker uses the exact same monkeypatched SessionLocal (isolated in-memory DB)
    import app.services.agents.agent_worker as agent_worker_mod
    import app.db.session as db_session_mod
    monkeypatch.setattr(agent_worker_mod, "SessionLocal", db_session_mod.SessionLocal)

    # Import SessionLocal, and models
    from app.db.session import SessionLocal
    from app.db.base import Base
    from app.models.client import Client
    from app.models.agents import (
        AgentDefinition,
        AgentRun,
        AgentRunStep,
        AgentRunEvent,
        AgentRunReceipt,
        AgentMemoryPolicy,
        AgentApprovalPolicy,
        AgentApprovalRequest,
        AgentTimelineEvent,
        AgentPolicyDecision,
        AgentTool
    )
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    # 2. Reset database to ensure clean schema and zero data leakage
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed Admin RBAC data since we dropped and recreated the tables
    from app.services.admin_rbac import ensure_admin_rbac_seed
    async with SessionLocal() as session:
        await ensure_admin_rbac_seed(session)
        await session.commit()


    
    # 3. Enforce that runtime is enabled. If runtime is disabled, the test fails.
    assert settings.agent_runtime_enabled is True, "Runtime disabled"
    assert settings.agent_execution_plane_enabled is True, "Execution plane disabled"
    
    # Set explicit runtime environment variables via python settings
    settings.agent_worker_enabled = True
    settings.agent_async_execution_enabled = True
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_observability_enabled = True
    settings.agent_executor_mock_mode = True  # Enable mock provider mode explicitly to avoid MockProviderError
    settings.agent_human_approval_enabled = True
    settings.agent_otel_tracing_enabled = True
    settings.agent_production_requires_eval_baseline = False


    admin_headers = {"X-Admin-Token": "test-admin-token"}

    # 4. Create client via Admin API
    client_resp = await e2e_client.post(
        "/admin/clients",
        json={"name": "E2E Agent Test Client"},
        headers=admin_headers
    )
    assert client_resp.status_code == 201
    client_data = client_resp.json()
    client_id = uuid.UUID(client_data["id"])

    # 5. Create API key via Admin API
    key_resp = await e2e_client.post(
        "/admin/api-keys",
        json={"client_id": str(client_id), "name": "E2E Key"},
        headers=admin_headers
    )
    assert key_resp.status_code == 201
    api_key_str = key_resp.json()["api_key"]

    # Seed the database policies and tools
    async with SessionLocal() as db:
        # 6. Create Memory Policy to satisfy memory write checks
        memory_policy = AgentMemoryPolicy(
            id=uuid.uuid4(),
            tenant_id=str(client_id),
            memory_type="short_term",
            retention_days=30,
            redaction_enabled=True,
            encryption_required=False,
            allow_export=True
        )
        db.add(memory_policy)

        # 7. Create Approval Policy for echo_tool calls
        approval_policy = AgentApprovalPolicy(
            id=uuid.uuid4(),
            name="Echo Tool Approval Policy",
            trigger_type="tool_call",
            tool_name="echo_tool",
            required_role="admin_write",
            enabled=True
        )
        db.add(approval_policy)

        # 8. Seed tool manually with correct risk_level to avoid seeding errors
        echo_tool = AgentTool(
            id=uuid.uuid4(),
            name="echo_tool",
            version="1.0.0",
            description="Echo input back",
            category="filesystem_safe",
            input_schema_json={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            },
            output_schema_json={
                "type": "object",
                "properties": {
                    "echo": {"type": "string"}
                }
            },
            risk_level="low",
            side_effect_level="none",
            timeout_seconds=30,
            enabled=True,
            requires_approval=False,
            scope="tenant"
        )
        db.add(echo_tool)
        await db.commit()

        # 9. Create Agent Definition
        agent_def = AgentDefinition(
            id=uuid.uuid4(),
            name="E2E Flow Agent",
            version="1.0.0",
            instructions="Execute workflow steps",
            model_id="mock-model",
            owner="e2e-tester",
            tenant_id=str(client_id),
            status="active",
            allowed_tools=["echo_tool"],
            max_steps=5,
            max_runtime_seconds=300
        )
        db.add(agent_def)
        await db.commit()

        agent_id = agent_def.id

    # 10. Configure explicit sequences of LLM responses
    responses = [
        # Step 1: Memory write
        {
            "type": "memory_write",
            "memory_type": "short_term",
            "content": "Access Code: E2E-999-PASS",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "cost_brl": 0.00075
        },
        # Step 2: Memory read
        {
            "type": "memory_read",
            "memory_type": "short_term",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "cost_brl": 0.00075
        },
        # Step 3: Tool Call (will require approval)
        {
            "type": "tool_call",
            "tool_name": "echo_tool",
            "tool_input": {"message": "Echo E2E message"},
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            "cost_brl": 0.001
        },
        # Step 4: Final output response
        {
            "type": "final",
            "output": "Finished executing. Code E2E-999-PASS and Tool hello verified.",
            "usage": {"prompt_tokens": 15, "completion_tokens": 10},
            "cost_brl": 0.0015
        }
    ]

    mock_llm = ExplicitMockLLMProvider(responses)
    # Monkeypatch the get_agent_llm_provider function to return our explicit mock
    monkeypatch.setattr(
        "app.services.agents.agent_llm_provider.get_agent_llm_provider",
        lambda db, proxy=None: mock_llm
    )
    monkeypatch.setattr(
        "app.services.agents.agent_executor.get_agent_llm_provider",
        lambda db, proxy=None: mock_llm
    )


    # 11. Start Agent Run via client E2E API
    headers = {"Authorization": f"Bearer {api_key_str}"}
    resp = await e2e_client.post(
        f"/v1/agents/{agent_id}/runs",
        json={"input_text": "Trigger e2e flow test"},
        headers=headers
    )
    assert resp.status_code == 200, f"Failed starting run: {resp.text}"
    run_id = uuid.UUID(resp.json()["id"])

    # 12. Verify worker picks up the job and executes steps
    worker = AgentWorkerService(worker_id="e2e-flow-worker")
    
    # Process Step 1 & 2 & 3 (stops at Step 3 tool call because it triggers approval request)
    processed = await worker.run_once()
    assert processed is True, "Worker failed to pick up and process job"

    # Check status: must be waiting_approval
    async with SessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        assert run.status == "waiting_approval", f"Expected status 'waiting_approval', got {run.status}. Reason: {run.failure_reason}"


        # 13. Assert Approval request exists
        stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run_id)
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        assert req is not None, "Expected AgentApprovalRequest to be created"
        assert req.status == "pending"
        assert req.sanitized_context["tool_name"] == "echo_tool"

        req_id = req.id

    # 14. Approve the request via HITL API
    approve_resp = await e2e_client.post(
        f"/admin/agent-approvals/{req_id}/approve",
        json={"reason": "Approved by E2E runner"},
        headers=admin_headers
    )
    assert approve_resp.status_code == 200, f"Approval endpoint failed: {approve_resp.text}"

    # 15. Resume execution: The HITL approval endpoint already re-enqueued and resumed the run.
    # We can immediately trigger the worker to process the next queued steps.


    # Process remaining steps (echo_tool tool execution & final response)
    processed_2 = await worker.run_once()
    assert processed_2 is True, "Worker failed to resume and process job"

    # 16. Verify final execution state
    async with SessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        assert run.status == "completed", f"Expected completed status, got {run.status}"
        # The hardened runtime records granular orchestration/model/tool/memory phases.
        assert run.total_steps >= 5, f"Expected granular step timeline, got {run.total_steps}"


        # 17. Check Receipts are generated
        stmt_rec = select(AgentRunReceipt).where(AgentRunReceipt.run_id == run_id)
        res_rec = await db.execute(stmt_rec)
        receipts = res_rec.scalars().all()
        assert len(receipts) > 0, "Expected step receipts to be generated"
        
        # Verify receipt structure & fields (receipt_data contains type, input_hash, output_hash, success)
        tool_receipts = [r for r in receipts if r.receipt_data["type"] == "tool_execution"]
        assert len(tool_receipts) == 1, "Expected exactly 1 tool_execution receipt"
        assert tool_receipts[0].receipt_data["success"] is True
        assert tool_receipts[0].signature is not None
        assert tool_receipts[0].receipt_data["input_hash"] is not None
        assert tool_receipts[0].receipt_data["output_hash"] is not None

        # 18. Check Run Events
        stmt_evt = select(AgentRunEvent).where(AgentRunEvent.run_id == run_id)
        res_evt = await db.execute(stmt_evt)
        run_events = res_evt.scalars().all()
        assert len(run_events) > 0, "Expected run events to be recorded"
        event_types = [e.event_type for e in run_events]
        assert "tool_call_completed" in event_types or "tool_call_started" in event_types
        assert "memory_write" in event_types
        assert "memory_read" in event_types


        # 19. Check Policy Decisions
        stmt_pol = select(AgentPolicyDecision).where(AgentPolicyDecision.run_id == run_id)
        res_pol = await db.execute(stmt_pol)
        policy_decisions = res_pol.scalars().all()
        assert len(policy_decisions) > 0, "Expected policy decisions to be recorded in db"
        action_types = [d.action_type for d in policy_decisions]
        assert "memory_write" in action_types
        assert "tool_call" in action_types

    # 20. Verify OpenTelemetry Observability trace generation endpoint
    trace_resp = await e2e_client.get(
        f"/admin/agents/observability/traces/{run_id}",
        headers=admin_headers
    )
    assert trace_resp.status_code == 200, f"Failed fetching trace: {trace_resp.text}"
    trace_data = trace_resp.json()
    assert "trace_id" in trace_data
    assert "span_id" in trace_data
    assert len(trace_data["spans"]) > 0, "Expected trace to contain child spans for steps"
