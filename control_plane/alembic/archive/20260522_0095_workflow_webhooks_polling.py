# Models: AgentWorkflowWebhookSubscription, AgentWorkflowPollingJob, AgentWorkflowExternalEvent
"""workflow webhooks and polling

Revision ID: 20260522_0095
Revises: 20260522_0094
Create Date: 2026-05-22 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260522_0095"
down_revision: str | None = "20260522_0094"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # 1. agent_workflow_webhook_subscriptions
    op.create_table(
        "agent_workflow_webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("secret_token", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_workflow_webhook_subscriptions_run_id"),
        "agent_workflow_webhook_subscriptions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_workflow_webhook_subscriptions_tenant_id"),
        "agent_workflow_webhook_subscriptions",
        ["tenant_id"],
        unique=False,
    )

    # 2. agent_workflow_polling_jobs
    op.create_table(
        "agent_workflow_polling_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("attempts_count", sa.Integer(), nullable=False),
        sa.Column("backoff_multiplier", sa.Float(), nullable=False),
        sa.Column("stop_condition", sa.JSON(), nullable=False),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_workflow_polling_jobs_run_id"),
        "agent_workflow_polling_jobs",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_workflow_polling_jobs_next_poll_at"),
        "agent_workflow_polling_jobs",
        ["next_poll_at"],
        unique=False,
    )

    # 3. agent_workflow_external_events
    op.create_table(
        "agent_workflow_external_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("event_source", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sanitized_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_workflow_external_events_run_id"),
        "agent_workflow_external_events",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("agent_workflow_external_events")
    op.drop_table("agent_workflow_polling_jobs")
    op.drop_table("agent_workflow_webhook_subscriptions")
