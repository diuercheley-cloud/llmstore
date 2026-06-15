"""phase61_opa_rego_policy_runtime

Revision ID: phase61_opa_rego_policy
Revises: 4b94becf3ca1
Create Date: 2026-05-15 15:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "phase61_opa_rego_policy"
down_revision = "4b94becf3ca1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_policy_runtime_bundles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bundle_hash", sa.String(length=128), nullable=False),
        sa.Column("rego_hash", sa.String(length=128), nullable=False),
        sa.Column("policy_namespace", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=False),
        sa.Column("previous_hash", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bundle_hash"),
    )
    op.create_index(
        op.f("ix_commercial_policy_runtime_bundles_bundle_hash"),
        "commercial_policy_runtime_bundles",
        ["bundle_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_runtime_bundles_policy_namespace"),
        "commercial_policy_runtime_bundles",
        ["policy_namespace"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_runtime_bundles_tenant_id"),
        "commercial_policy_runtime_bundles",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "commercial_policy_evaluations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bundle_id", sa.UUID(), nullable=False),
        sa.Column("evaluation_mode", sa.String(length=32), nullable=False),
        sa.Column("enforcement_result", sa.String(length=32), nullable=False),
        sa.Column("decision_trace", sa.JSON(), nullable=False),
        sa.Column("runtime_hash", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["commercial_policy_runtime_bundles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_policy_evaluations_bundle_id"),
        "commercial_policy_evaluations",
        ["bundle_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_evaluations_tenant_id"),
        "commercial_policy_evaluations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_evaluations_created_at"),
        "commercial_policy_evaluations",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "commercial_policy_simulations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bundle_id", sa.UUID(), nullable=False),
        sa.Column("simulation_name", sa.String(length=255), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("expected_result", sa.String(length=32), nullable=True),
        sa.Column("actual_result", sa.String(length=32), nullable=False),
        sa.Column("diff_trace", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["commercial_policy_runtime_bundles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_policy_simulations_bundle_id"),
        "commercial_policy_simulations",
        ["bundle_id"],
        unique=False,
    )

    op.create_table(
        "commercial_policy_decision_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evaluation_id", sa.UUID(), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column("action_taken", sa.String(length=32), nullable=False),
        sa.Column("context_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["commercial_policy_evaluations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_policy_decision_logs_evaluation_id"),
        "commercial_policy_decision_logs",
        ["evaluation_id"],
        unique=False,
    )

    op.create_table(
        "commercial_policy_violations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evaluation_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("violation_code", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("remediation_hints", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["commercial_policy_evaluations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_policy_violations_evaluation_id"),
        "commercial_policy_violations",
        ["evaluation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_violations_tenant_id"),
        "commercial_policy_violations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_policy_violations_violation_code"),
        "commercial_policy_violations",
        ["violation_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("commercial_policy_violations")
    op.drop_table("commercial_policy_decision_logs")
    op.drop_table("commercial_policy_simulations")
    op.drop_table("commercial_policy_evaluations")
    op.drop_table("commercial_policy_runtime_bundles")
