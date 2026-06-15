"""phase47_confidential_runtime

Revision ID: 31a7b456d2e1
Revises: f637b1293c40
Create Date: 2026-05-15 13:19:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "31a7b456d2e1"
down_revision = "f637b1293c40"
branch_labels = None
depends_on = None


def upgrade():
    # 1. CommercialConfidentialRuntimeProfile
    op.create_table(
        "commercial_confidential_runtime_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_name", sa.String(length=128), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("require_encrypted_input", sa.Boolean(), nullable=True),
        sa.Column("require_encrypted_output", sa.Boolean(), nullable=True),
        sa.Column("prohibit_prompt_logging", sa.Boolean(), nullable=True),
        sa.Column("prohibit_response_logging", sa.Boolean(), nullable=True),
        sa.Column("require_runtime_attestation", sa.Boolean(), nullable=True),
        sa.Column("require_model_trust", sa.Boolean(), nullable=True),
        sa.Column("max_retention_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_confidential_runtime_profiles_client_id"),
        "commercial_confidential_runtime_profiles",
        ["client_id"],
        unique=False,
    )

    # 2. CommercialConfidentialInferenceSession
    op.create_table(
        "commercial_confidential_inference_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("encryption_key_id", sa.String(length=128), nullable=True),
        sa.Column("input_mode", sa.String(length=32), nullable=True),
        sa.Column("output_mode", sa.String(length=32), nullable=True),
        sa.Column("attestation_status", sa.String(length=32), nullable=True),
        sa.Column("model_trust_state", sa.String(length=64), nullable=True),
        sa.Column("retention_policy_applied", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["commercial_confidential_runtime_profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_confidential_inference_sessions_client_id"),
        "commercial_confidential_inference_sessions",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_confidential_inference_sessions_request_id"),
        "commercial_confidential_inference_sessions",
        ["request_id"],
        unique=False,
    )

    # 3. CommercialConfidentialRuntimeAuditEvent
    op.create_table(
        "commercial_confidential_runtime_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["commercial_confidential_inference_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_confidential_runtime_audit_events_event_type"),
        "commercial_confidential_runtime_audit_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_confidential_runtime_audit_events_immutable_hash"),
        "commercial_confidential_runtime_audit_events",
        ["immutable_hash"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_commercial_confidential_runtime_audit_events_immutable_hash"),
        table_name="commercial_confidential_runtime_audit_events",
    )
    op.drop_index(
        op.f("ix_commercial_confidential_runtime_audit_events_event_type"),
        table_name="commercial_confidential_runtime_audit_events",
    )
    op.drop_table("commercial_confidential_runtime_audit_events")
    op.drop_index(
        op.f("ix_commercial_confidential_inference_sessions_request_id"),
        table_name="commercial_confidential_inference_sessions",
    )
    op.drop_index(
        op.f("ix_commercial_confidential_inference_sessions_client_id"),
        table_name="commercial_confidential_inference_sessions",
    )
    op.drop_table("commercial_confidential_inference_sessions")
    op.drop_index(
        op.f("ix_commercial_confidential_runtime_profiles_client_id"),
        table_name="commercial_confidential_runtime_profiles",
    )
    op.drop_table("commercial_confidential_runtime_profiles")
