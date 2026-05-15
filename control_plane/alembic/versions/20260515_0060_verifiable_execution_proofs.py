"""Phase 60 Verifiable AI Execution Proofs + Merkle Audit Timelines

Revision ID: 20260515_0060
Revises: 20260515_0059
Create Date: 2026-05-15 04:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0060"
down_revision = "20260515_0059"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # CommercialMerkleTimeline
    op.create_table(
        "commercial_merkle_timelines",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("timeline_type", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("leaf_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("merkle_root", sa.String(length=128), nullable=False),
        sa.Column("previous_timeline_root", sa.String(length=128), nullable=True),
        sa.Column("timeline_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="building"),
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timeline_hash"),
    )
    op.create_index("ix_commercial_merkle_timelines_type", "commercial_merkle_timelines", ["timeline_type"])
    op.create_index("ix_commercial_merkle_timelines_status", "commercial_merkle_timelines", ["status"])
    op.create_index("ix_commercial_merkle_timelines_root", "commercial_merkle_timelines", ["merkle_root"])
    op.create_index("ix_commercial_merkle_timelines_prev_root", "commercial_merkle_timelines", ["previous_timeline_root"])
    op.create_index("ix_commercial_merkle_timelines_period", "commercial_merkle_timelines", ["period_start", "period_end"])

    # CommercialMerkleLeaf
    op.create_table(
        "commercial_merkle_leaves",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("timeline_id", _uuid_type(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("leaf_hash", sa.String(length=128), nullable=False),
        sa.Column("leaf_index", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["timeline_id"], ["commercial_merkle_timelines.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_merkle_leaves_timeline_id", "commercial_merkle_leaves", ["timeline_id"])
    op.create_index("ix_commercial_merkle_leaves_source", "commercial_merkle_leaves", ["source_type", "source_id"])
    op.create_index("ix_commercial_merkle_leaves_leaf_hash", "commercial_merkle_leaves", ["leaf_hash"])

    # CommercialExecutionProof
    op.create_table(
        "commercial_execution_proofs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("receipt_id", _uuid_type(), nullable=True),
        sa.Column("timeline_id", _uuid_type(), nullable=False),
        sa.Column("proof_type", sa.String(length=32), nullable=False),
        sa.Column("proof_json", sa.JSON(), nullable=False),
        sa.Column("proof_hash", sa.String(length=128), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["receipt_id"], ["commercial_inference_receipts.id"]),
        sa.ForeignKeyConstraint(["timeline_id"], ["commercial_merkle_timelines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proof_hash"),
    )
    op.create_index("ix_commercial_execution_proofs_receipt_id", "commercial_execution_proofs", ["receipt_id"])
    op.create_index("ix_commercial_execution_proofs_timeline_id", "commercial_execution_proofs", ["timeline_id"])
    op.create_index("ix_commercial_execution_proofs_type", "commercial_execution_proofs", ["proof_type"])
    op.create_index("ix_commercial_execution_proofs_status", "commercial_execution_proofs", ["verification_status"])


def downgrade() -> None:
    op.drop_table("commercial_execution_proofs")
    op.drop_table("commercial_merkle_leaves")
    op.drop_table("commercial_merkle_timelines")
