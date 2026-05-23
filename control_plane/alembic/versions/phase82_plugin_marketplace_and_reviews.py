"""Add plugin marketplace tables and plugin reviews

Revision ID: phase82_plugin_marketplace
Revises: 20260519_0086
Create Date: 2026-05-19 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "phase82_plugin_marketplace"
down_revision = "20260519_0086"
branch_labels = None
depends_on = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return sa.UUID()


def _json_type():
    return sa.JSON()


def upgrade() -> None:
    uuid_type = _uuid_type()
    json_type = _json_type()

    op.create_table(
        "plugin_marketplace_entries",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("license", sa.String(length=128), nullable=False),
        sa.Column("plugin_type", sa.String(length=64), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_plugin_marketplace_entries_name"), "plugin_marketplace_entries", ["name"], unique=True)

    op.create_table(
        "plugin_versions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("plugin_entry_id", uuid_type, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("download_url", sa.String(length=1024), nullable=True),
        sa.Column("manifest_json", json_type, nullable=False),
        sa.Column("min_platform_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plugin_entry_id"], ["plugin_marketplace_entries.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_versions_plugin_entry_id"), "plugin_versions", ["plugin_entry_id"], unique=False)

    op.create_table(
        "plugin_installs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("plugin_entry_id", uuid_type, nullable=False),
        sa.Column("current_version_id", uuid_type, nullable=False),
        sa.Column("install_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'installed'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config_json", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plugin_entry_id"], ["plugin_marketplace_entries.id"], ),
        sa.ForeignKeyConstraint(["current_version_id"], ["plugin_versions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_installs_plugin_entry_id"), "plugin_installs", ["plugin_entry_id"], unique=False)

    op.create_table(
        "plugin_permissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("plugin_install_id", uuid_type, nullable=False),
        sa.Column("permission_name", sa.String(length=255), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plugin_install_id"], ["plugin_installs.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_permissions_plugin_install_id"), "plugin_permissions", ["plugin_install_id"], unique=False)

    op.create_table(
        "plugin_trust_reports",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("plugin_version_id", uuid_type, nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vulnerabilities_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("report_details", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_signed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("signer_identity", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["plugin_version_id"], ["plugin_versions.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_trust_reports_plugin_version_id"), "plugin_trust_reports", ["plugin_version_id"], unique=False)

    op.create_table(
        "plugin_reviews",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("plugin_entry_id", uuid_type, nullable=False),
        sa.Column("admin_user_id", uuid_type, nullable=True),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plugin_entry_id"], ["plugin_marketplace_entries.id"], ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_reviews_plugin_entry_id"), "plugin_reviews", ["plugin_entry_id"], unique=False)
    op.create_index(op.f("ix_plugin_reviews_admin_user_id"), "plugin_reviews", ["admin_user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("plugin_reviews")
    op.drop_table("plugin_trust_reports")
    op.drop_table("plugin_permissions")
    op.drop_table("plugin_installs")
    op.drop_table("plugin_versions")
    op.drop_table("plugin_marketplace_entries")
