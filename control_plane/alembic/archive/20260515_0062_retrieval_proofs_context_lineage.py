"""Phase 49 Retrieval Proofs + Explainable Context Lineage

Revision ID: 20260515_0062
Revises: 20260515_0061
Create Date: 2026-05-15 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_0062"
down_revision = "20260515_0061"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_retrieval_proofs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("retrieval_audit_id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("timeline_id", _uuid_type(), nullable=True),
        sa.Column("proof_hash", sa.String(length=128), nullable=False),
        sa.Column("policy_hash", sa.String(length=128), nullable=False),
        sa.Column("lineage_root_hash", sa.String(length=128), nullable=False),
        sa.Column("retrieval_sent_hash", sa.String(length=128), nullable=False),
        sa.Column("merkle_root", sa.String(length=128), nullable=False),
        sa.Column("proof_json", sa.JSON(), nullable=False),
        sa.Column(
            "verification_status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("export_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["retrieval_audit_id"], ["commercial_rag_retrieval_audits.id"]),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.ForeignKeyConstraint(["timeline_id"], ["commercial_merkle_timelines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proof_hash"),
    )
    op.create_index(
        "ix_commercial_retrieval_proofs_retrieval_audit_id",
        "commercial_retrieval_proofs",
        ["retrieval_audit_id"],
    )
    op.create_index(
        "ix_commercial_retrieval_proofs_vault_id", "commercial_retrieval_proofs", ["vault_id"]
    )
    op.create_index(
        "ix_commercial_retrieval_proofs_timeline_id", "commercial_retrieval_proofs", ["timeline_id"]
    )
    op.create_index(
        "ix_commercial_retrieval_proofs_lineage_root_hash",
        "commercial_retrieval_proofs",
        ["lineage_root_hash"],
    )

    op.create_table(
        "commercial_context_lineages",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("retrieval_proof_id", _uuid_type(), nullable=False),
        sa.Column("parent_lineage_id", _uuid_type(), nullable=True),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("node_hash", sa.String(length=128), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retrieval_proof_id"], ["commercial_retrieval_proofs.id"]),
        sa.ForeignKeyConstraint(["parent_lineage_id"], ["commercial_context_lineages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_context_lineages_retrieval_proof_id",
        "commercial_context_lineages",
        ["retrieval_proof_id"],
    )
    op.create_index(
        "ix_commercial_context_lineages_parent_lineage_id",
        "commercial_context_lineages",
        ["parent_lineage_id"],
    )
    op.create_index(
        "ix_commercial_context_lineages_node_hash", "commercial_context_lineages", ["node_hash"]
    )

    op.create_table(
        "commercial_retrieval_merkle_leaves",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("retrieval_proof_id", _uuid_type(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("leaf_hash", sa.String(length=128), nullable=False),
        sa.Column("leaf_index", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retrieval_proof_id"], ["commercial_retrieval_proofs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_retrieval_merkle_leaves_retrieval_proof_id",
        "commercial_retrieval_merkle_leaves",
        ["retrieval_proof_id"],
    )
    op.create_index(
        "ix_commercial_retrieval_merkle_leaves_leaf_hash",
        "commercial_retrieval_merkle_leaves",
        ["leaf_hash"],
    )

    op.create_table(
        "commercial_retrieval_replay_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("retrieval_proof_id", _uuid_type(), nullable=False),
        sa.Column("replay_hash", sa.String(length=128), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("drift_status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("drift_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["retrieval_proof_id"], ["commercial_retrieval_proofs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_retrieval_replay_records_retrieval_proof_id",
        "commercial_retrieval_replay_records",
        ["retrieval_proof_id"],
    )
    op.create_index(
        "ix_commercial_retrieval_replay_records_replay_hash",
        "commercial_retrieval_replay_records",
        ["replay_hash"],
    )


def downgrade() -> None:
    op.drop_table("commercial_retrieval_replay_records")
    op.drop_table("commercial_retrieval_merkle_leaves")
    op.drop_table("commercial_context_lineages")
    op.drop_table("commercial_retrieval_proofs")
