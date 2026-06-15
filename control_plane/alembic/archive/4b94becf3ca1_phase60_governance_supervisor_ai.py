"""phase60_governance_supervisor_ai

Revision ID: 4b94becf3ca1
Revises: d9f24aa93e5f
Create Date: 2026-05-15 14:56:59.259086
"""

import sqlalchemy as sa
from alembic import op

revision = "4b94becf3ca1"
down_revision = "d9f24aa93e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_governance_supervisor_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_type", sa.String(length=64), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_policies_policy_type"),
        "commercial_governance_supervisor_policies",
        ["policy_type"],
        unique=False,
    )

    op.create_table(
        "commercial_governance_supervisor_risk_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("overall_risk_score", sa.Float(), nullable=False),
        sa.Column("financial_risk", sa.Float(), nullable=False),
        sa.Column("compliance_risk", sa.Float(), nullable=False),
        sa.Column("qos_risk", sa.Float(), nullable=False),
        sa.Column("security_risk", sa.Float(), nullable=False),
        sa.Column("risk_factors", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_risk_scores_client_id"),
        "commercial_governance_supervisor_risk_scores",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_risk_scores_calculated_at"),
        "commercial_governance_supervisor_risk_scores",
        ["calculated_at"],
        unique=False,
    )

    op.create_table(
        "commercial_governance_supervisor_incidents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("triggering_signals", sa.JSON(), nullable=False),
        sa.Column("correlated_anomalies", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_incidents_client_id"),
        "commercial_governance_supervisor_incidents",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_incidents_incident_type"),
        "commercial_governance_supervisor_incidents",
        ["incident_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_incidents_status"),
        "commercial_governance_supervisor_incidents",
        ["status"],
        unique=False,
    )

    op.create_table(
        "commercial_governance_supervisor_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.UUID(), nullable=True),
        sa.Column("policy_id", sa.UUID(), nullable=True),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.JSON(), nullable=False),
        sa.Column("mode_used", sa.String(length=32), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["commercial_governance_supervisor_incidents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["commercial_governance_supervisor_policies.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_decisions_incident_id"),
        "commercial_governance_supervisor_decisions",
        ["incident_id"],
        unique=False,
    )

    op.create_table(
        "commercial_governance_supervisor_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_resource_type", sa.String(length=64), nullable=False),
        sa.Column("target_resource_id", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("rollback_hook", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["commercial_governance_supervisor_decisions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_actions_decision_id"),
        "commercial_governance_supervisor_actions",
        ["decision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_governance_supervisor_actions_status"),
        "commercial_governance_supervisor_actions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("commercial_governance_supervisor_actions")
    op.drop_table("commercial_governance_supervisor_decisions")
    op.drop_table("commercial_governance_supervisor_incidents")
    op.drop_table("commercial_governance_supervisor_risk_scores")
    op.drop_table("commercial_governance_supervisor_policies")
