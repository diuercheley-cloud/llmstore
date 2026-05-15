"""tenant_encryption_controls

Revision ID: 20260514_0054
Revises: 20260514_0053
Create Date: 2026-05-15 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260514_0054"
down_revision = "20260514_0053"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "commercial_tenant_encryption_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_version", sa.String(length=64), nullable=False),
        sa.Column("key_purpose", sa.String(length=64), nullable=False),
        sa.Column("key_status", sa.String(length=32), nullable=False),
        sa.Column("wrapped_key", sa.Text(), nullable=True),
        sa.Column("key_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("rotation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_tenant_encryption_keys_client_id", "commercial_tenant_encryption_keys", ["client_id"], unique=False)
    op.create_index("ix_commercial_tenant_encryption_keys_key_purpose", "commercial_tenant_encryption_keys", ["key_purpose"], unique=False)
    op.create_index("ix_commercial_tenant_encryption_keys_key_status", "commercial_tenant_encryption_keys", ["key_status"], unique=False)
    op.create_index("ix_commercial_tenant_encryption_keys_key_fingerprint", "commercial_tenant_encryption_keys", ["key_fingerprint"], unique=False)

    op.create_table(
        "commercial_encrypted_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("encryption_mode", sa.String(length=32), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["key_id"], ["commercial_tenant_encryption_keys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_encrypted_artifacts_client_id", "commercial_encrypted_artifacts", ["client_id"], unique=False)
    op.create_index("ix_commercial_encrypted_artifacts_artifact_type", "commercial_encrypted_artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_commercial_encrypted_artifacts_resource_type", "commercial_encrypted_artifacts", ["resource_type"], unique=False)
    op.create_index("ix_commercial_encrypted_artifacts_resource_id", "commercial_encrypted_artifacts", ["resource_id"], unique=False)

    op.create_table(
        "commercial_encryption_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("key_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_encryption_audit_events_client_id", "commercial_encryption_audit_events", ["client_id"], unique=False)
    op.create_index("ix_commercial_encryption_audit_events_event_type", "commercial_encryption_audit_events", ["event_type"], unique=False)

def downgrade():
    op.drop_table("commercial_encryption_audit_events")
    op.drop_table("commercial_encrypted_artifacts")
    op.drop_table("commercial_tenant_encryption_keys")
