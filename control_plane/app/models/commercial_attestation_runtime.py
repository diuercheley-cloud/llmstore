import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialRuntimeAttestation(Base):
    __tablename__ = "commercial_runtime_attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    runtime_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    firmware_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workflow_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    evidence_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_chain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attestation_mode: Mapped[str] = mapped_column(String(32), default="software_attested", nullable=False, index=True)
    enclave_type: Mapped[str] = mapped_column(String(32), default="software_attested", nullable=False)
    platform_type: Mapped[str] = mapped_column(String(64), default="linux_x86_64", nullable=False)

    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    drift_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    measurement_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialAttestationEvidence(Base):
    __tablename__ = "commercial_attestation_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runtime_attestation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=True,
    )
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    evidence_type: Mapped[str] = mapped_column(String(32), default="runtime_measurement", nullable=False, index=True)
    evidence_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    previous_evidence_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chain_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    enclave_type: Mapped[str] = mapped_column(String(32), default="software_attested", nullable=False)
    platform_type: Mapped[str] = mapped_column(String(64), default="linux_x86_64", nullable=False)
    attestation_mode: Mapped[str] = mapped_column(String(32), default="software_attested", nullable=False)

    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    signed_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_algorithm: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialAttestationPolicy(Base):
    __tablename__ = "commercial_attestation_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    min_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_drift_threshold: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    require_signed_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_measurement_chain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_model_binding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_workflow_binding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_enclave_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allowed_platform_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    enforcement_mode: Mapped[str] = mapped_column(String(32), default="report_only", nullable=False)
    block_untrusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_for_sovereign: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_for_sensitive_tenants: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialRuntimeMeasurement(Base):
    __tablename__ = "commercial_runtime_measurements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runtime_attestation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=True,
    )
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    measurement_type: Mapped[str] = mapped_column(String(32), default="runtime_binary", nullable=False, index=True)
    measurement_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_chain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    previous_measurement_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_path_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    drift_reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    environment_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    measurement_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialAttestationChallenge(Base):
    __tablename__ = "commercial_attestation_challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    challenge_nonce: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    challenge_type: Mapped[str] = mapped_column(String(32), default="runtime_measurement", nullable=False)
    challenge_data_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_data_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    response_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    response_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_result: Mapped[str | None] = mapped_column(String(32), nullable=True)

    required_measurements_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trust_score_required: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
