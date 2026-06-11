from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import yaml
from app.models.agents.agent_workflows import AgentWorkflowDefinition, AgentWorkflowEdge, AgentWorkflowNode
from app.models.agents.agents import AgentDefinition, AgentMemoryIndex, AgentMemoryItem
from app.models.agents.immutable_audit import ImmutableAuditLog
from app.models.billing.billing_invoice import BillingInvoice
from app.models.billing.billing_plan import BillingPlan
from app.models.core.auth import OAuthState, UserSession
from app.models.core.client import Client
from app.models.core.admin_rbac import AdminAuditEvent
from app.models.governance.policy_engine import DeterministicPolicy, PolicyEvaluationResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class RecoveryIds:
    agent_id: uuid.UUID
    workflow_id: uuid.UUID
    memory_item_id: uuid.UUID
    memory_index_id: uuid.UUID
    billing_plan_id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    oauth_state_id: uuid.UUID
    user_session_id: uuid.UUID
    policy_id: str
    policy_eval_id: str


def prepare_repo_tree(repo_root: Path) -> None:
    (repo_root / "config").mkdir(parents=True, exist_ok=True)
    (repo_root / "VERSION").write_text("2026.06.11-dr\n", encoding="utf-8")
    (repo_root / "config" / "app.yaml").write_text(
        "tenant_mode: dedicated\nbilling_provider: internal\nretention_days: 90\n",
        encoding="utf-8",
    )
    (repo_root / "config" / "feature-flags.yaml").write_text(
        "flags:\n  restore_guard: true\n  billing_reconciliation: true\n",
        encoding="utf-8",
    )


async def seed_recovery_state(
    session: AsyncSession,
    repo_root: Path,
    *,
    extra_agents: int = 0,
    long_text_size: int = 0,
) -> RecoveryIds:
    tenant_id = "tenant-dr-primary"
    agent_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    memory_item_id = uuid.uuid4()
    memory_index_id = uuid.uuid4()
    billing_plan_id = uuid.uuid4()
    client_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    oauth_state_id = uuid.uuid4()
    user_session_id = uuid.uuid4()
    policy_id = f"policy-{uuid.uuid4().hex[:12]}"
    policy_eval_id = f"policy-eval-{uuid.uuid4().hex[:12]}"

    instructions = "Recover all persisted control-plane state."
    if long_text_size:
        instructions = instructions + "\n" + ("A" * long_text_size)

    agent = AgentDefinition(
        id=agent_id,
        name="DR Control Agent",
        version="2.1.0",
        instructions=instructions,
        model_id="gpt-test",
        owner="platform-ops",
        tenant_id=tenant_id,
        status="active",
    )
    workflow = AgentWorkflowDefinition(
        id=workflow_id,
        tenant_id=tenant_id,
        name="tenant-recovery",
        version="1.0.0",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        metadata_json={"domain": "operations", "critical": True},
    )
    workflow_node = AgentWorkflowNode(
        workflow_definition_id=workflow_id,
        node_key="start",
        node_type="task",
        config={"action": "recover"},
        metadata_json={"retry": 3},
    )
    workflow_edge = AgentWorkflowEdge(
        workflow_definition_id=workflow_id,
        from_node_key="start",
        to_node_key="start",
        metadata_json={"loop": False},
    )
    memory_item = AgentMemoryItem(
        id=memory_item_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        collection_id=None,
        memory_type="vector",
        content_hash="seed-hash",
        raw_content="critical tenant recovery context",
        provenance={"source": "backup-dr-test"},
        retention_until=datetime.now(UTC) + timedelta(days=90),
    )
    memory_index = AgentMemoryIndex(
        id=memory_index_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        memory_item_id=memory_item_id,
        index_status="completed",
        vector_id="vec-dr-1",
        embedding="[0.01,0.02,0.03]",
    )

    billing_plan = BillingPlan(
        id=billing_plan_id,
        code="enterprise-dr",
        name="Enterprise DR",
        description="Priority DR plan",
        rate_limit_per_minute=5000,
        daily_token_quota=5_000_000,
        weekly_token_quota=25_000_000,
        monthly_token_quota=100_000_000,
        max_output_tokens=16384,
        max_context_tokens=131072,
        requests_per_day=50000,
        requests_per_month=1_500_000,
        rag_enabled=True,
        rag_max_documents=5000,
        rag_max_storage_mb=4096,
        rag_max_pages_per_month=50_000,
        rag_max_queries_per_month=250_000,
        tts_enabled=True,
        embeddings_enabled=True,
        responses_enabled=True,
        tools_enabled=True,
        export_enabled=True,
        support_level="Enterprise",
        price_brl=Decimal("999.90"),
        allowed_models_json=json.dumps(["gpt-test", "gpt-ops"]),
        routing_policy_json=json.dumps({"mode": "priority"}),
    )
    client = Client(
        id=client_id,
        name="tenant-dr-client",
        description="Primary DR tenant client",
        billing_status="active",
        billing_plan_id=billing_plan_id,
        metadata_json=json.dumps({"tenant_id": tenant_id}),
    )
    invoice = BillingInvoice(
        id=invoice_id,
        client_id=client_id,
        billing_plan_id=billing_plan_id,
        status="issued",
        currency="USD",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        monthly_price=Decimal("999.90"),
        included_tokens=10_000_000,
        used_tokens=3_500_000,
        overage_tokens=50_000,
        overage_price_per_1k_tokens=Decimal("0.015000"),
        overage_cost=Decimal("0.750000"),
        total_amount=Decimal("1000.650000"),
        payment_instructions="Wire transfer within 15 days",
        due_at=datetime.now(UTC) + timedelta(days=15),
    )

    oauth_state = OAuthState(
        id=oauth_state_id,
        provider="sso",
        state="restore-state-token",
        redirect_uri="https://tenant.example/callback",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        used=False,
    )
    user_session = UserSession(
        id=user_session_id,
        provider="sso",
        provider_user_id="user-123",
        email="ops@tenant.example",
        name="Ops User",
        tenant_id=tenant_id,
        session_token="session-token-original",
        expires_at=datetime.now(UTC) + timedelta(hours=8),
        is_active=True,
    )

    immutable_audit = ImmutableAuditLog(
        tenant_id=tenant_id,
        action="restore.plan.generated",
        actor="ops-user",
        payload=json.dumps({"billing": "ok", "auth": "ok"}),
        previous_hash="0" * 64,
        hash="1" * 64,
        signature="sig-immutable-audit",
    )
    admin_audit = AdminAuditEvent(
        event_type="backup.restore.requested",
        status="success",
        actor_identifier="ops-user",
        target_type="backup",
        target_id="seed-backup",
        metadata_json={"tenant_id": tenant_id},
    )

    policy = DeterministicPolicy(
        id=policy_id,
        client_id=client_id,
        policy_name="restore-approval",
        policy_scope="tenant",
        policy_version="2026.06",
        policy_dsl=json.dumps({"allow": ["restore"], "deny": ["unsafe_delete"]}),
        policy_hash="2" * 64,
        policy_status="active",
        immutable_hash="3" * 64,
    )
    policy_eval = PolicyEvaluationResult(
        id=policy_eval_id,
        client_id=client_id,
        policy_id=policy_id,
        subject_type="backup",
        subject_ref="seed-backup",
        evaluation_status="completed",
        decision="allow",
        explanation="Approved by deterministic DR policy",
        replay_safe=True,
        immutable_hash="4" * 64,
    )

    session.add_all(
        [
            agent,
            workflow,
            workflow_node,
            workflow_edge,
            memory_item,
            memory_index,
            billing_plan,
            client,
            invoice,
            oauth_state,
            user_session,
            immutable_audit,
            admin_audit,
            policy,
            policy_eval,
        ]
    )

    for index in range(extra_agents):
        session.add(
            AgentDefinition(
                id=uuid.uuid4(),
                name=f"Bulk Agent {index}",
                version="1.0.0",
                instructions=instructions,
                model_id="gpt-test",
                owner="bulk-loader",
                tenant_id=tenant_id,
                status="active",
            )
        )

    await session.commit()
    prepare_repo_tree(repo_root)

    return RecoveryIds(
        agent_id=agent_id,
        workflow_id=workflow_id,
        memory_item_id=memory_item_id,
        memory_index_id=memory_index_id,
        billing_plan_id=billing_plan_id,
        client_id=client_id,
        invoice_id=invoice_id,
        oauth_state_id=oauth_state_id,
        user_session_id=user_session_id,
        policy_id=policy_id,
        policy_eval_id=policy_eval_id,
    )


async def collect_recovery_state(session: AsyncSession, repo_root: Path, ids: RecoveryIds) -> dict[str, object]:
    agent = await session.get(AgentDefinition, ids.agent_id)
    workflow = await session.get(AgentWorkflowDefinition, ids.workflow_id)
    memory_index = await session.get(AgentMemoryIndex, ids.memory_index_id)
    billing_plan = await session.get(BillingPlan, ids.billing_plan_id)
    client = await session.get(Client, ids.client_id)
    invoice = await session.get(BillingInvoice, ids.invoice_id)
    oauth_state = await session.get(OAuthState, ids.oauth_state_id)
    user_session = await session.get(UserSession, ids.user_session_id)
    policy = await session.get(DeterministicPolicy, ids.policy_id)
    policy_eval = await session.get(PolicyEvaluationResult, ids.policy_eval_id)

    immutable_audit = (
        await session.execute(
            select(ImmutableAuditLog).where(ImmutableAuditLog.tenant_id == "tenant-dr-primary").limit(1)
        )
    ).scalar_one()
    admin_audit = (
        await session.execute(
            select(AdminAuditEvent).where(AdminAuditEvent.event_type == "backup.restore.requested").limit(1)
        )
    ).scalar_one()

    return {
        "tenant": {
            "agent_name": agent.name,
            "agent_tenant_id": agent.tenant_id,
            "workflow_name": workflow.name,
            "memory_vector_id": memory_index.vector_id,
        },
        "billing": {
            "plan_name": billing_plan.name,
            "client_name": client.name,
            "invoice_total": str(invoice.total_amount),
        },
        "auth": {
            "oauth_state": oauth_state.state,
            "session_token": user_session.session_token,
            "tenant_id": user_session.tenant_id,
        },
        "audit": {
            "immutable_payload": immutable_audit.payload,
            "admin_status": admin_audit.status,
        },
        "policies": {
            "policy_hash": policy.policy_hash,
            "policy_status": policy.policy_status,
            "policy_decision": policy_eval.decision,
        },
        "persisted_config": {
            "app_yaml": yaml.safe_load((repo_root / "config" / "app.yaml").read_text(encoding="utf-8")),
            "feature_flags": yaml.safe_load((repo_root / "config" / "feature-flags.yaml").read_text(encoding="utf-8")),
            "version": (repo_root / "VERSION").read_text(encoding="utf-8").strip(),
        },
    }


async def mutate_recovery_state(session: AsyncSession, repo_root: Path, ids: RecoveryIds) -> None:
    agent = await session.get(AgentDefinition, ids.agent_id)
    workflow = await session.get(AgentWorkflowDefinition, ids.workflow_id)
    memory_index = await session.get(AgentMemoryIndex, ids.memory_index_id)
    billing_plan = await session.get(BillingPlan, ids.billing_plan_id)
    invoice = await session.get(BillingInvoice, ids.invoice_id)
    oauth_state = await session.get(OAuthState, ids.oauth_state_id)
    user_session = await session.get(UserSession, ids.user_session_id)
    policy = await session.get(DeterministicPolicy, ids.policy_id)
    policy_eval = await session.get(PolicyEvaluationResult, ids.policy_eval_id)

    agent.name = "Mutated Agent"
    workflow.name = "mutated-workflow"
    memory_index.vector_id = "vec-mutated"
    billing_plan.name = "Mutated Plan"
    invoice.total_amount = Decimal("42.000000")
    oauth_state.state = "mutated-state"
    user_session.session_token = "mutated-session-token"
    policy.policy_hash = "9" * 64
    policy.policy_status = "disabled"
    policy_eval.decision = "deny"
    await session.commit()

    (repo_root / "config" / "app.yaml").write_text("tenant_mode: broken\n", encoding="utf-8")
    (repo_root / "config" / "feature-flags.yaml").write_text("flags:\n  restore_guard: false\n", encoding="utf-8")
    (repo_root / "VERSION").write_text("mutated-version\n", encoding="utf-8")
