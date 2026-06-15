"""add_commercial_infra_executions

Revision ID: 8a6cd3ddb494
Revises: f899d30584c3
Create Date: 2026-05-14 17:47:04.744132
"""

import sqlalchemy as sa
from alembic import op

revision = "8a6cd3ddb494"
down_revision = "f899d30584c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_infra_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("simulation_id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("adapter", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("target_scope", sa.String(), nullable=False),
        sa.Column("target_identifier", sa.String(), nullable=False),
        sa.Column("requested_action_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=True),
        sa.Column("leader_node_id", sa.String(), nullable=True),
        sa.Column("fencing_token", sa.String(), nullable=True),
        sa.Column("external_operation_id", sa.String(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["commercial_approval_records.id"],
        ),
        sa.ForeignKeyConstraint(
            ["simulation_id"],
            ["commercial_infra_simulations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_action_type"),
        "commercial_infra_executions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_adapter"),
        "commercial_infra_executions",
        ["adapter"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_approval_id"),
        "commercial_infra_executions",
        ["approval_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_simulation_id"),
        "commercial_infra_executions",
        ["simulation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_status"),
        "commercial_infra_executions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_target_identifier"),
        "commercial_infra_executions",
        ["target_identifier"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_infra_executions_target_scope"),
        "commercial_infra_executions",
        ["target_scope"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_commercial_infra_executions_target_scope"),
        table_name="commercial_infra_executions",
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_target_identifier"),
        table_name="commercial_infra_executions",
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_status"), table_name="commercial_infra_executions"
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_simulation_id"),
        table_name="commercial_infra_executions",
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_approval_id"), table_name="commercial_infra_executions"
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_adapter"), table_name="commercial_infra_executions"
    )
    op.drop_index(
        op.f("ix_commercial_infra_executions_action_type"), table_name="commercial_infra_executions"
    )
    op.drop_table("commercial_infra_executions")
