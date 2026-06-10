"""phase58_hardware_attestation_runtime

Revision ID: 20260515_phase58
Revises: 20260515_phase57
Create Date: 2026-05-15 23:58:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_phase58"
down_revision = "20260515_phase57"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _uuid_type():
    return postgresql.UUID(as_uuid=True) if _dialect_name() == "postgresql" else sa.String(length=36)


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if _dialect_name() == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "commercial_runtime_attestations",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("runtime_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("firmware_hash", sa.String(length=128), nullable=True),
        sa.Column("model_hash", sa.String(length=128), nullable=True),
        sa.Column("workflow_hash", sa.String(length=128), nullable=True),
        sa.Column("policy_hash", sa.String(length=128), nullable=True),
        sa.Column("evidence_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("measurement_chain_hash", sa.String(length=128), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("attestation_mode", sa.String(length=32), nullable=False, index=True),
        sa.Column("enclave_type", sa.String(length=32), nullable=False),
        sa.Column("platform_type", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("previous_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("drift_detected", sa.Boolean(), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("trusted", sa.Boolean(), nullable=False),
        sa.Column("evidence_json", _json_type(), nullable=False),
        sa.Column("measurement_json", _json_type(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_runtime_attestations_lookup", "commercial_runtime_attestations",
                    ["cluster_id", "node_id", "status"], unique=False)
    op.create_index("ix_commercial_runtime_attestations_chain", "commercial_runtime_attestations",
                    ["immutable_hash", "previous_hash"], unique=False)
    op.create_index("ix_commercial_runtime_attestations_trust", "commercial_runtime_attestations",
                    ["trusted", "trust_score", "drift_detected"], unique=False)

    op.create_table(
        "commercial_attestation_evidence",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("runtime_attestation_id", _uuid_type(), nullable=True, index=True),
        sa.Column("node_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("evidence_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("evidence_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("previous_evidence_hash", sa.String(length=128), nullable=True),
        sa.Column("chain_position", sa.Integer(), nullable=False),
        sa.Column("enclave_type", sa.String(length=32), nullable=False),
        sa.Column("platform_type", sa.String(length=64), nullable=False),
        sa.Column("attestation_mode", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", _json_type(), nullable=False),
        sa.Column("signed_evidence", sa.Text(), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_attestation_evidence_chain", "commercial_attestation_evidence",
                    ["evidence_hash", "previous_evidence_hash", "chain_position"], unique=False)
    op.create_index("ix_commercial_attestation_evidence_scope", "commercial_attestation_evidence",
                    ["cluster_id", "evidence_type", "status"], unique=False)

    op.create_table(
        "commercial_attestation_policies",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("policy_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("min_trust_score", sa.Float(), nullable=False),
        sa.Column("max_drift_threshold", sa.Float(), nullable=False),
        sa.Column("require_signed_evidence", sa.Boolean(), nullable=False),
        sa.Column("require_measurement_chain", sa.Boolean(), nullable=False),
        sa.Column("require_model_binding", sa.Boolean(), nullable=False),
        sa.Column("require_workflow_binding", sa.Boolean(), nullable=False),
        sa.Column("allowed_enclave_types_json", _json_type(), nullable=False),
        sa.Column("allowed_platform_types_json", _json_type(), nullable=False),
        sa.Column("enforcement_mode", sa.String(length=32), nullable=False),
        sa.Column("block_untrusted", sa.Boolean(), nullable=False),
        sa.Column("require_for_sovereign", sa.Boolean(), nullable=False),
        sa.Column("require_for_sensitive_tenants", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_attestation_policies_active", "commercial_attestation_policies",
                    ["policy_name", "is_active", "policy_hash"], unique=False)

    op.create_table(
        "commercial_runtime_measurements",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("runtime_attestation_id", _uuid_type(), nullable=True, index=True),
        sa.Column("node_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("measurement_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("measurement_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("measurement_chain_hash", sa.String(length=128), nullable=True),
        sa.Column("previous_measurement_hash", sa.String(length=128), nullable=True),
        sa.Column("object_name", sa.String(length=255), nullable=True),
        sa.Column("object_version", sa.String(length=64), nullable=True),
        sa.Column("object_path_hash", sa.String(length=128), nullable=True),
        sa.Column("expected_hash", sa.String(length=128), nullable=True),
        sa.Column("observed_hash", sa.String(length=128), nullable=True),
        sa.Column("drift_detected", sa.Boolean(), nullable=False),
        sa.Column("drift_reasons_json", _json_type(), nullable=False),
        sa.Column("environment_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("measurement_json", _json_type(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_runtime_measurements_chain", "commercial_runtime_measurements",
                    ["measurement_hash", "previous_measurement_hash", "measurement_type"], unique=False)
    op.create_index("ix_commercial_runtime_measurements_scope", "commercial_runtime_measurements",
                    ["cluster_id", "measurement_type", "status"], unique=False)

    op.create_table(
        "commercial_attestation_challenges",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("challenge_nonce", sa.String(length=128), nullable=False, unique=True, index=True),
        sa.Column("challenge_type", sa.String(length=32), nullable=False),
        sa.Column("challenge_data_json", _json_type(), nullable=False),
        sa.Column("response_data_json", _json_type(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("response_received", sa.Boolean(), nullable=False),
        sa.Column("response_valid", sa.Boolean(), nullable=False),
        sa.Column("verification_result", sa.String(length=32), nullable=True),
        sa.Column("required_measurements_json", _json_type(), nullable=False),
        sa.Column("trust_score_required", sa.Float(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_attestation_challenges_nonce", "commercial_attestation_challenges",
                    ["challenge_nonce", "status", "expires_at"], unique=False)
    op.create_index("ix_commercial_attestation_challenges_scope", "commercial_attestation_challenges",
                    ["cluster_id", "node_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_commercial_attestation_challenges_scope", table_name="commercial_attestation_challenges")
    op.drop_index("ix_commercial_attestation_challenges_nonce", table_name="commercial_attestation_challenges")
    op.drop_table("commercial_attestation_challenges")
    op.drop_index("ix_commercial_runtime_measurements_scope", table_name="commercial_runtime_measurements")
    op.drop_index("ix_commercial_runtime_measurements_chain", table_name="commercial_runtime_measurements")
    op.drop_table("commercial_runtime_measurements")
    op.drop_index("ix_commercial_attestation_policies_active", table_name="commercial_attestation_policies")
    op.drop_table("commercial_attestation_policies")
    op.drop_index("ix_commercial_attestation_evidence_scope", table_name="commercial_attestation_evidence")
    op.drop_index("ix_commercial_attestation_evidence_chain", table_name="commercial_attestation_evidence")
    op.drop_table("commercial_attestation_evidence")
    op.drop_index("ix_commercial_runtime_attestations_trust", table_name="commercial_runtime_attestations")
    op.drop_index("ix_commercial_runtime_attestations_chain", table_name="commercial_runtime_attestations")
    op.drop_index("ix_commercial_runtime_attestations_lookup", table_name="commercial_runtime_attestations")
    op.drop_table("commercial_runtime_attestations")
