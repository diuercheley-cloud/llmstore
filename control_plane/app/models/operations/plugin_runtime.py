# Owner: platform-ops
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

PLUGIN_CONTRACT_SCOPES = (
    "adapter",
    "workflow",
    "governance",
    "remediation",
    "attestation",
    "federation",
    "mixed",
)

PLUGIN_CONTRACT_STATUSES = (
    "draft",
    "active",
    "deprecated",
    "blocked",
    "revoked",
)

PLUGIN_COMPATIBILITY_STATUSES = (
    "compatible",
    "incompatible",
    "warning",
    "blocked",
)

PLUGIN_LOAD_STATUSES = (
    "proposed",
    "validated",
    "blocked",
    "simulated",
    "executed",
)

PLUGIN_ISOLATION_LEVELS = (
    "strict",
    "sovereign",
    "airgap",
    "sandbox_only",
)

PLUGIN_LIFECYCLE_EVENT_TYPES = (
    "submitted",
    "reviewed",
    "compatibility_checked",
    "sandbox_validated",
    "placeholder_certified",
    "activated",
    "executed",
    "deprecated",
    "revoked",
    "blocked",
)

PLUGIN_LIFECYCLE_STATUSES = (
    "accepted",
    "denied",
    "warning",
)

PLUGIN_VERIFICATION_STATUSES = (
    "passed",
    "failed",
    "warning",
)

PLUGIN_FEDERATION_STATUSES = (
    "compatible",
    "incompatible",
    "warning",
    "blocked",
)


class PluginABIContract(Base):
    __tablename__ = "plugin_abi_contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    plugin_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    abi_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    contract_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginCapabilityBoundary(Base):
    __tablename__ = "plugin_capability_boundaries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    allowed_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    denied_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    isolation_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_only: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    network_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    subprocess_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    filesystem_write_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    external_secret_access_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginRuntimeCompatibilityCheck(Base):
    __tablename__ = "plugin_runtime_compatibility_checks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    runtime_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    compatibility_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    federation_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class DeterministicExtensionLoadPlan(Base):
    __tablename__ = "deterministic_extension_load_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    load_order: Mapped[str] = mapped_column(Text(), nullable=False)
    load_plan_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    load_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginIsolationPolicy(Base):
    __tablename__ = "plugin_isolation_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    isolation_level: Mapped[str] = mapped_column(String(32), nullable=False, default="strict", index=True)
    deny_network: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deny_subprocess: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deny_dynamic_import: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deny_external_filesystem_write: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deny_plaintext_secret_access: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginLifecycleEvent(Base):
    __tablename__ = "plugin_lifecycle_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    lifecycle_event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginReplayVerificationResult(Base):
    __tablename__ = "plugin_replay_verification_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deterministic_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginFederationCompatibility(Base):
    __tablename__ = "plugin_federation_compatibility"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_environment: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_environment: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    federation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    compatibility_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginRuntimeReceipt(Base):
    __tablename__ = "plugin_runtime_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginRuntimeActivation(Base):
    __tablename__ = "plugin_runtime_activations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    load_plan_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("deterministic_extension_load_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    activation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="prepared", index=True)
    runtime_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="sandboxed")
    artifact_locator: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class PluginRuntimeExecution(Base):
    __tablename__ = "plugin_runtime_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    abi_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    activation_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("plugin_runtime_activations.id", ondelete="SET NULL"), nullable=True, index=True)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)
    runtime_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="sandboxed")
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
