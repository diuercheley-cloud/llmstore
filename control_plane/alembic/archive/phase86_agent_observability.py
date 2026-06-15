# Models: AgentIncident, AgentIncidentEvent, AgentRunMetrics, AgentRunCosts, AgentTraceSpan, AgentTimelineEvent
"""Agent Observability Models

Revision ID: phase86_agent_observability
Revises: phase85_agent_eval_gates
Create Date: 2026-05-22 15:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "phase86_agent_observability"
down_revision: Union[str, None] = "phase85_agent_eval_gates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_incidents
    op.create_table(
        "agent_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("acknowledged_by", sa.String(length=128), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_incidents_tenant_id"), "agent_incidents", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_incidents_agent_id"), "agent_incidents", ["agent_id"], unique=False
    )
    op.create_index(op.f("ix_agent_incidents_run_id"), "agent_incidents", ["run_id"], unique=False)

    # 2. agent_incident_events
    op.create_table(
        "agent_incident_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("performed_by", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["agent_incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_incident_events_incident_id"),
        "agent_incident_events",
        ["incident_id"],
        unique=False,
    )

    # 3. agent_run_metrics
    op.create_table(
        "agent_run_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tool_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tool_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_policy_denials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_memory_reads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_memory_writes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_approval_waits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_approval_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_handoffs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_run_metrics_run_id"), "agent_run_metrics", ["run_id"], unique=False
    )

    # 4. agent_run_costs
    op.create_table(
        "agent_run_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_brl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_run_costs_run_id"), "agent_run_costs", ["run_id"], unique=False)
    op.create_index(
        op.f("ix_agent_run_costs_agent_id"), "agent_run_costs", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_run_costs_tenant_id"), "agent_run_costs", ["tenant_id"], unique=False
    )

    # 5. agent_trace_spans
    op.create_table(
        "agent_trace_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("parent_span_id", sa.String(length=64), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("span_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attributes_json", sa.JSON(), nullable=False),
        sa.Column("events_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_trace_spans_trace_id"), "agent_trace_spans", ["trace_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_trace_spans_span_id"), "agent_trace_spans", ["span_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_trace_spans_run_id"), "agent_trace_spans", ["run_id"], unique=False
    )

    # 6. agent_timeline_events
    op.create_table(
        "agent_timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("is_error", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_timeline_events_run_id"), "agent_timeline_events", ["run_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("agent_timeline_events")
    op.drop_table("agent_trace_spans")
    op.drop_table("agent_run_costs")
    op.drop_table("agent_run_metrics")
    op.drop_table("agent_incident_events")
    op.drop_table("agent_incidents")
