"""administrative RBAC

Revision ID: 20260518_0083
Revises: 20260518_0082
Create Date: 2026-05-18 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_0083"
down_revision = "20260518_0082"
branch_labels = None
depends_on = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return sa.UUID()


def upgrade() -> None:
    uuid_type = _uuid_type()

    op.create_table(
        "admin_users",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_legacy_bootstrap", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_users_username"), "admin_users", ["username"], unique=True)
    op.create_index(op.f("ix_admin_users_email"), "admin_users", ["email"], unique=True)
    op.create_index(
        op.f("ix_admin_users_token_prefix"), "admin_users", ["token_prefix"], unique=False
    )
    op.create_index(op.f("ix_admin_users_is_active"), "admin_users", ["is_active"], unique=False)

    op.create_table(
        "admin_roles",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_roles_name"), "admin_roles", ["name"], unique=True)

    op.create_table(
        "admin_permissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_permissions_code"), "admin_permissions", ["code"], unique=True)

    op.create_table(
        "admin_user_roles",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("role_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["admin_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_admin_user_roles_user_role"),
    )
    op.create_index(
        op.f("ix_admin_user_roles_user_id"), "admin_user_roles", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_admin_user_roles_role_id"), "admin_user_roles", ["role_id"], unique=False
    )

    op.create_table(
        "admin_role_permissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("role_id", uuid_type, nullable=False),
        sa.Column("permission_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["admin_permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["admin_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id", "permission_id", name="uq_admin_role_permissions_role_permission"
        ),
    )
    op.create_index(
        op.f("ix_admin_role_permissions_role_id"),
        "admin_role_permissions",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_role_permissions_permission_id"),
        "admin_role_permissions",
        ["permission_id"],
        unique=False,
    )

    op.create_table(
        "admin_audit_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("admin_user_id", uuid_type, nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("target_type", sa.String(length=120), nullable=True),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("actor_identifier", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_events_admin_user_id"),
        "admin_audit_events",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_events_event_type"), "admin_audit_events", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_admin_audit_events_status"), "admin_audit_events", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_admin_audit_events_created_at"), "admin_audit_events", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_events_created_at"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_status"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_event_type"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_admin_user_id"), table_name="admin_audit_events")
    op.drop_table("admin_audit_events")

    op.drop_index(
        op.f("ix_admin_role_permissions_permission_id"), table_name="admin_role_permissions"
    )
    op.drop_index(op.f("ix_admin_role_permissions_role_id"), table_name="admin_role_permissions")
    op.drop_table("admin_role_permissions")

    op.drop_index(op.f("ix_admin_user_roles_role_id"), table_name="admin_user_roles")
    op.drop_index(op.f("ix_admin_user_roles_user_id"), table_name="admin_user_roles")
    op.drop_table("admin_user_roles")

    op.drop_index(op.f("ix_admin_permissions_code"), table_name="admin_permissions")
    op.drop_table("admin_permissions")

    op.drop_index(op.f("ix_admin_roles_name"), table_name="admin_roles")
    op.drop_table("admin_roles")

    op.drop_index(op.f("ix_admin_users_is_active"), table_name="admin_users")
    op.drop_index(op.f("ix_admin_users_token_prefix"), table_name="admin_users")
    op.drop_index(op.f("ix_admin_users_email"), table_name="admin_users")
    op.drop_index(op.f("ix_admin_users_username"), table_name="admin_users")
    op.drop_table("admin_users")
