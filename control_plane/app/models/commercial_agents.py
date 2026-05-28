import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialAgentProfile(Base):
    __tablename__ = "commercial_agent_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    base_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allowed_tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    system_prompt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    requires_approval_for_tools: Mapped[bool] = mapped_column(Boolean, default=True)
    can_delegate: Mapped[bool] = mapped_column(Boolean, default=False)
    max_delegation_depth: Mapped[int] = mapped_column(Integer, default=1)

    memory_isolation_mode: Mapped[str] = mapped_column(String(32), default="strict")
    confidential_runtime_required: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_tenants_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    agent_permissions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    max_actions_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    max_actions_per_day: Mapped[int] = mapped_column(Integer, default=2000)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialAgentExecution(Base):
    __tablename__ = "commercial_agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_profiles.id"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    parent_execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plan_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    execution_graph_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    runtime_snapshot_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    audit_chain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    policy_decision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    replay_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    runtime_mode: Mapped[str] = mapped_column(String(32), default="enforce")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str] = mapped_column(String(32), default="not_required", index=True)
    confidential_payload_mode: Mapped[str] = mapped_column(String(32), default="redacted")
    quota_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialAgentDelegationPolicy(Base):
    __tablename__ = "commercial_agent_delegation_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_profiles.id"),
        nullable=False,
    )
    target_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_profiles.id"),
        nullable=False,
    )
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    constraints_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialAgentToolExecution(Base):
    __tablename__ = "commercial_agent_tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_executions.id"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialAgentMemoryBoundary(Base):
    __tablename__ = "commercial_agent_memory_boundaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_executions.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    boundary_type: Mapped[str] = mapped_column(String(32), default="session")
    access_log_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialAgentAction(Base):
    __tablename__ = "commercial_agent_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_executions.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_index: Mapped[int] = mapped_column(Integer, nullable=False)
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    planned_input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_envelope_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    previous_action_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    graph_node_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    detached_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_algorithm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_decision_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sandbox_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidential_mode: Mapped[str] = mapped_column(String(32), default="redacted")
    approval_status: Mapped[str] = mapped_column(String(32), default="not_required", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialToolRegistry(Base):
    __tablename__ = "commercial_tool_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trust_status: Mapped[str] = mapped_column(String(32), default="trusted", index=True)
    provenance_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provenance_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    signer_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(32), default="internal")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    confidential_payload_mode: Mapped[str] = mapped_column(String(32), default="redacted")
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=120)
    quota_limit_per_day: Mapped[int] = mapped_column(Integer, default=5000)
    policy_scope_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialToolApproval(Base):
    __tablename__ = "commercial_tool_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_actions.id"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_executions.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_chain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialAgentReplayRecord(Base):
    __tablename__ = "commercial_agent_replay_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_agent_executions.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replay_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    original_plan_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_graph_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_snapshot_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    replay_graph_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_result: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    mismatch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
