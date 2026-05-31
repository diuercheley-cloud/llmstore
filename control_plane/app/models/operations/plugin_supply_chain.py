from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

PLUGIN_PROVENANCE_SCOPES = (
    "plugin",
    "abi_contract",
    "extension_bundle",
    "federation_bundle",
    "governance_artifact",
)

PLUGIN_PROVENANCE_STATUSES = (
    "proposed",
    "verified",
    "warning",
    "blocked",
    "revoked",
)

PLUGIN_DEPENDENCY_VERIFICATION_STATUSES = (
    "passed",
    "failed",
    "warning",
    "blocked",
)

PLUGIN_SIGNATURE_STATUSES = (
    "signature_only",
    "revoked",
    "blocked",
)


class PluginProvenanceRecord(Base):
    __tablename__ = "plugin_provenance_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_abi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    artifact_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provenance_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provenance_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginSBOMPlaceholder(Base):
    __tablename__ = "plugin_sbom_placeholders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_provenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    sbom_format: Mapped[str] = mapped_column(String(64), nullable=False, default="placeholder_v1", index=True)
    dependency_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    denied_dependencies_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reproducible_build: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    sbom_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginArtifactLineage(Base):
    __tablename__ = "plugin_artifact_lineage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_provenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class DependencyGovernancePolicy(Base):
    __tablename__ = "dependency_governance_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    denied_dependency_classes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    allowed_dependency_classes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    require_reproducible_builds: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    require_offline_verification: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    require_signature: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginDependencyVerification(Base):
    __tablename__ = "plugin_dependency_verifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_provenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    dependency_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginSignedArtifact(Base):
    __tablename__ = "plugin_signed_artifact_placeholders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_provenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="provenance_record", index=True)
    signature_status: Mapped[str] = mapped_column(String(32), nullable=False, default="signature_only", index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class PluginSupplyChainReceipt(Base):
    __tablename__ = "plugin_supply_chain_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("plugin_provenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
