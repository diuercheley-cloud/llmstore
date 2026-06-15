# Models: AgentToolCredential, AgentToolCredentialGrant, AgentToolExecutionSandbox, AgentToolSideEffect, AgentToolRollbackAction, AgentToolQuotaCounter, AgentToolExecutionAudit
"""Agent Tool Execution tables

Revision ID: phase84_agent_tool_execution
Revises: phase83_agent_execution_plane
Create Date: 2026-05-22 13:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "phase84_agent_tool_execution"
down_revision: Union[str, None] = "phase83_agent_execution_plane"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_tool_credentials
    op.create_table(
        "agent_tool_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("credential_type", sa.String(length=32), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("secret_masked", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_credentials_tenant_id"),
        "agent_tool_credentials",
        ["tenant_id"],
        unique=False,
    )

    # 2. agent_tool_credential_grants
    op.create_table(
        "agent_tool_credential_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["agent_tool_credentials.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["agent_tool_id"], ["agent_tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_credential_grants_credential_id"),
        "agent_tool_credential_grants",
        ["credential_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_credential_grants_agent_id"),
        "agent_tool_credential_grants",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_credential_grants_agent_tool_id"),
        "agent_tool_credential_grants",
        ["agent_tool_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_credential_grants_tenant_id"),
        "agent_tool_credential_grants",
        ["tenant_id"],
        unique=False,
    )

    # 3. agent_tool_execution_sandboxes
    op.create_table(
        "agent_tool_execution_sandboxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invocation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("sandbox_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("allowed_commands", sa.JSON(), nullable=False),
        sa.Column("runtime_limit_seconds", sa.Integer(), nullable=False),
        sa.Column("output_limit_bytes", sa.Integer(), nullable=False),
        sa.Column("output_truncated", sa.Boolean(), nullable=False),
        sa.Column("output_log", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["invocation_id"], ["agent_tool_invocations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_execution_sandboxes_invocation_id"),
        "agent_tool_execution_sandboxes",
        ["invocation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_execution_sandboxes_tenant_id"),
        "agent_tool_execution_sandboxes",
        ["tenant_id"],
        unique=False,
    )

    # 4. agent_tool_side_effects
    op.create_table(
        "agent_tool_side_effects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invocation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("side_effect_level", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.String(length=256), nullable=True),
        sa.Column("change_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invocation_id"], ["agent_tool_invocations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_side_effects_invocation_id"),
        "agent_tool_side_effects",
        ["invocation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_side_effects_tenant_id"),
        "agent_tool_side_effects",
        ["tenant_id"],
        unique=False,
    )

    # 5. agent_tool_rollback_actions
    op.create_table(
        "agent_tool_rollback_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("side_effect_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("compensation_action", sa.Text(), nullable=False),
        sa.Column("compensation_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["side_effect_id"], ["agent_tool_side_effects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_rollback_actions_side_effect_id"),
        "agent_tool_rollback_actions",
        ["side_effect_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_rollback_actions_tenant_id"),
        "agent_tool_rollback_actions",
        ["tenant_id"],
        unique=False,
    )

    # 6. agent_tool_quota_counters
    op.create_table(
        "agent_tool_quota_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_tool_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("side_effect_level", sa.String(length=32), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invocation_count", sa.Integer(), nullable=False),
        sa.Column("max_limit", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_quota_counters_tenant_id"),
        "agent_tool_quota_counters",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_quota_counters_agent_id"),
        "agent_tool_quota_counters",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_quota_counters_agent_tool_id"),
        "agent_tool_quota_counters",
        ["agent_tool_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_quota_counters_window_start"),
        "agent_tool_quota_counters",
        ["window_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_quota_counters_window_end"),
        "agent_tool_quota_counters",
        ["window_end"],
        unique=False,
    )

    # 7. agent_tool_execution_audit
    op.create_table(
        "agent_tool_execution_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invocation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_tool_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_tool_execution_audit_invocation_id"),
        "agent_tool_execution_audit",
        ["invocation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_execution_audit_tenant_id"),
        "agent_tool_execution_audit",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_execution_audit_agent_id"),
        "agent_tool_execution_audit",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_execution_audit_agent_tool_id"),
        "agent_tool_execution_audit",
        ["agent_tool_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tool_execution_audit_event_type"),
        "agent_tool_execution_audit",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("agent_tool_execution_audit")
    op.drop_table("agent_tool_quota_counters")
    op.drop_table("agent_tool_rollback_actions")
    op.drop_table("agent_tool_side_effects")
    op.drop_table("agent_tool_execution_sandboxes")
    op.drop_table("agent_tool_credential_grants")
    op.drop_table("agent_tool_credentials")
