"""phase44_witness_federation

Revision ID: 4dae4ba9d504
Revises: 20260515_0060
Create Date: 2026-05-15 09:50:59.387726
"""
import sqlalchemy as sa
from alembic import op

revision = '4dae4ba9d504'
down_revision = '20260515_0060'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Witnesses
    op.create_table(
        "commercial_witnesses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("witness_name", sa.String(length=255), nullable=False),
        sa.Column("witness_type", sa.String(length=50), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("trust_level", sa.String(length=50), server_default="medium", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )

    # 2. Quorum Policies
    op.create_table(
        "commercial_witness_quorum_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("timeline_type", sa.String(length=100), nullable=False),
        sa.Column("required_signatures", sa.Integer(), server_default="1", nullable=False),
        sa.Column("allowed_witnesses_json", sa.JSON(), nullable=True),
        sa.Column("require_external_witness", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )

    # 3. Signatures
    op.create_table(
        "commercial_witness_signatures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("timeline_id", sa.UUID(), nullable=False),
        sa.Column("witness_id", sa.UUID(), nullable=False),
        sa.Column("merkle_root", sa.String(length=255), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("signature_algorithm", sa.String(length=50), nullable=False),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.Column("verification_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["timeline_id"], ["commercial_merkle_timelines.id"]),
        sa.ForeignKeyConstraint(["witness_id"], ["commercial_witnesses.id"]),
        sa.PrimaryKeyConstraint("id")
    )

    # 4. Audit Events
    op.create_table(
        "commercial_witness_audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("witness_id", sa.UUID(), nullable=True),
        sa.Column("timeline_id", sa.UUID(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    op.drop_table("commercial_witness_audit_events")
    op.drop_table("commercial_witness_signatures")
    op.drop_table("commercial_witness_quorum_policies")
    op.drop_table("commercial_witnesses")

