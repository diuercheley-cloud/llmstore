"""Phase 39 runtime model integrity monitor

Revision ID: 20260515_0057
Revises: 20260515_0056
Create Date: 2026-05-15 02:15:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_0057"
down_revision = "20260515_0056"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_model_integrity_scans",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("registry_entry_id", _uuid_type(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("scan_type", sa.String(length=32), nullable=False),
        sa.Column("expected_checksum", sa.String(length=128), nullable=True),
        sa.Column("observed_checksum", sa.String(length=128), nullable=True),
        sa.Column("integrity_status", sa.String(length=32), nullable=False),
        sa.Column("scan_duration_ms", sa.Integer(), nullable=True),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registry_entry_id"], ["commercial_signed_model_registry_entries.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_registry_entry_id"),
        "commercial_model_integrity_scans",
        ["registry_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_model_name"),
        "commercial_model_integrity_scans",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_scan_type"),
        "commercial_model_integrity_scans",
        ["scan_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_integrity_status"),
        "commercial_model_integrity_scans",
        ["integrity_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_node_id"),
        "commercial_model_integrity_scans",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_scans_cluster_id"),
        "commercial_model_integrity_scans",
        ["cluster_id"],
        unique=False,
    )

    op.create_table(
        "commercial_runtime_model_attestations",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("registry_entry_id", _uuid_type(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("backend_name", sa.String(length=255), nullable=True),
        sa.Column("model_alias", sa.String(length=128), nullable=True),
        sa.Column("expected_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("observed_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("expected_checksum", sa.String(length=128), nullable=True),
        sa.Column("observed_checksum", sa.String(length=128), nullable=True),
        sa.Column("attestation_status", sa.String(length=32), nullable=False),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["registry_entry_id"], ["commercial_signed_model_registry_entries.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_registry_entry_id"),
        "commercial_runtime_model_attestations",
        ["registry_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_model_name"),
        "commercial_runtime_model_attestations",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_backend_name"),
        "commercial_runtime_model_attestations",
        ["backend_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_model_alias"),
        "commercial_runtime_model_attestations",
        ["model_alias"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_attestation_status"),
        "commercial_runtime_model_attestations",
        ["attestation_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_node_id"),
        "commercial_runtime_model_attestations",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_runtime_model_attestations_cluster_id"),
        "commercial_runtime_model_attestations",
        ["cluster_id"],
        unique=False,
    )

    op.create_table(
        "commercial_model_integrity_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("registry_entry_id", _uuid_type(), nullable=True),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registry_entry_id"], ["commercial_signed_model_registry_entries.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_model_name"),
        "commercial_model_integrity_events",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_event_type"),
        "commercial_model_integrity_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_severity"),
        "commercial_model_integrity_events",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_registry_entry_id"),
        "commercial_model_integrity_events",
        ["registry_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_node_id"),
        "commercial_model_integrity_events",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_cluster_id"),
        "commercial_model_integrity_events",
        ["cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_model_integrity_events_immutable_hash"),
        "commercial_model_integrity_events",
        ["immutable_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_immutable_hash"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_cluster_id"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_node_id"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_registry_entry_id"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_severity"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_event_type"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_events_model_name"),
        table_name="commercial_model_integrity_events",
    )
    op.drop_table("commercial_model_integrity_events")

    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_cluster_id"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_node_id"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_attestation_status"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_model_alias"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_backend_name"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_model_name"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_index(
        op.f("ix_commercial_runtime_model_attestations_registry_entry_id"),
        table_name="commercial_runtime_model_attestations",
    )
    op.drop_table("commercial_runtime_model_attestations")

    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_cluster_id"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_node_id"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_integrity_status"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_scan_type"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_model_name"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_index(
        op.f("ix_commercial_model_integrity_scans_registry_entry_id"),
        table_name="commercial_model_integrity_scans",
    )
    op.drop_table("commercial_model_integrity_scans")
