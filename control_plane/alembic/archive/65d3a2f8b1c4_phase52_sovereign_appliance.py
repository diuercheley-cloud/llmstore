"""phase52_sovereign_appliance

Revision ID: 65d3a2f8b1c4
Revises: e72a4c1b6d3f
Create Date: 2026-05-15 14:14:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "65d3a2f8b1c4"
down_revision = "e72a4c1b6d3f"
branch_labels = None
depends_on = None


def upgrade():
    # 1. CommercialApplianceProfile
    op.create_table(
        "commercial_appliance_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appliance_id", sa.String(length=128), nullable=False),
        sa.Column("deployment_tier", sa.String(length=64), nullable=True),
        sa.Column("is_offline_first", sa.Boolean(), nullable=True),
        sa.Column("require_removable_media_auth", sa.Boolean(), nullable=True),
        sa.Column("strict_chain_of_custody", sa.Boolean(), nullable=True),
        sa.Column("last_sync_hash", sa.String(length=128), nullable=True),
        sa.Column("health_status", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appliance_id"),
    )

    # 2. CommercialOfflineSyncManifest
    op.create_table(
        "commercial_offline_sync_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appliance_id", sa.String(length=128), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("sync_direction", sa.String(length=32), nullable=True),
        sa.Column("payload_type", sa.String(length=64), nullable=False),
        sa.Column("media_uuid", sa.String(length=128), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["appliance_id"],
            ["commercial_appliance_profiles.appliance_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_offline_sync_manifests_manifest_hash"),
        "commercial_offline_sync_manifests",
        ["manifest_hash"],
        unique=False,
    )

    # 3. CommercialOfflineModelBundle
    op.create_table(
        "commercial_offline_model_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_hash", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("signed_registry_hash", sa.String(length=128), nullable=True),
        sa.Column("promotion_status", sa.String(length=32), nullable=True),
        sa.Column("manifest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["commercial_offline_sync_manifests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_offline_model_bundles_bundle_hash"),
        "commercial_offline_model_bundles",
        ["bundle_hash"],
        unique=False,
    )

    # 4. CommercialOfflineAuditPackage
    op.create_table(
        "commercial_offline_audit_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_hash", sa.String(length=128), nullable=False),
        sa.Column("time_window_start", sa.DateTime(), nullable=False),
        sa.Column("time_window_end", sa.DateTime(), nullable=False),
        sa.Column("includes_receipts", sa.Boolean(), nullable=True),
        sa.Column("includes_governance_logs", sa.Boolean(), nullable=True),
        sa.Column("export_status", sa.String(length=32), nullable=True),
        sa.Column("manifest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["commercial_offline_sync_manifests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_offline_audit_packages_package_hash"),
        "commercial_offline_audit_packages",
        ["package_hash"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_commercial_offline_audit_packages_package_hash"),
        table_name="commercial_offline_audit_packages",
    )
    op.drop_table("commercial_offline_audit_packages")
    op.drop_index(
        op.f("ix_commercial_offline_model_bundles_bundle_hash"),
        table_name="commercial_offline_model_bundles",
    )
    op.drop_table("commercial_offline_model_bundles")
    op.drop_index(
        op.f("ix_commercial_offline_sync_manifests_manifest_hash"),
        table_name="commercial_offline_sync_manifests",
    )
    op.drop_table("commercial_offline_sync_manifests")
    op.drop_table("commercial_appliance_profiles")
