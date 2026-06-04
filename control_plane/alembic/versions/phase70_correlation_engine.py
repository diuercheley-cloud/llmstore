"""Phase 70 Deterministic Operations Correlation Engine

Revision ID: phase70_correlation_engine
Revises: phase69_failure_signals
Create Date: 2026-05-15 19:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "phase70_correlation_engine"
down_revision = "phase69_failure_signals"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. OperationalCorrelation
    op.create_table(
        "operational_correlations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_type", sa.String(length=100), nullable=False),
        sa.Column("source_domains_json", sa.JSON(), nullable=False),
        sa.Column("correlation_key", sa.String(length=255), nullable=False),
        sa.Column("correlation_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_operational_correlations_client_id", "operational_correlations", ["client_id"], unique=False)
    op.create_index("ix_operational_correlations_correlation_type", "operational_correlations", ["correlation_type"], unique=False)
    op.create_index("ix_operational_correlations_correlation_key", "operational_correlations", ["correlation_key"], unique=False)
    op.create_index("ix_operational_correlations_immutable_hash", "operational_correlations", ["immutable_hash"], unique=False)

    # 2. CorrelatedOperationalEvent
    op.create_table(
        "correlated_operational_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source_domain", sa.String(length=100), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["correlation_id"], ["operational_correlations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_correlated_operational_events_client_id", "correlated_operational_events", ["client_id"], unique=False)
    op.create_index("ix_correlated_operational_events_correlation_id", "correlated_operational_events", ["correlation_id"], unique=False)
    op.create_index("ix_correlated_operational_events_event_type", "correlated_operational_events", ["event_type"], unique=False)
    op.create_index("ix_correlated_operational_events_source_domain", "correlated_operational_events", ["source_domain"], unique=False)
    op.create_index("ix_correlated_operational_events_immutable_hash", "correlated_operational_events", ["immutable_hash"], unique=False)

    # 3. OperationalTrustLink
    op.create_table(
        "operational_trust_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node", sa.String(length=255), nullable=False),
        sa.Column("target_node", sa.String(length=255), nullable=False),
        sa.Column("trust_relation", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_operational_trust_links_client_id", "operational_trust_links", ["client_id"], unique=False)
    op.create_index("ix_operational_trust_links_source_node", "operational_trust_links", ["source_node"], unique=False)
    op.create_index("ix_operational_trust_links_target_node", "operational_trust_links", ["target_node"], unique=False)
    op.create_index("ix_operational_trust_links_immutable_hash", "operational_trust_links", ["immutable_hash"], unique=False)

def downgrade() -> None:
    op.drop_table("operational_trust_links")
    op.drop_table("correlated_operational_events")
    op.drop_table("operational_correlations")
