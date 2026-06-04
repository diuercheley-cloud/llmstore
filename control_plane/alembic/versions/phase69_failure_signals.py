"""Phase 69 Predictive Failure Signals + Deterministic Forecasting

Revision ID: phase69_failure_signals
Revises: phase66_predictive_aiops
Create Date: 2026-05-15 18:07:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "phase69_failure_signals"
down_revision = "phase66_predictive_aiops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations_failure_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("source_domain", sa.String(64), nullable=False),
        sa.Column("source_ref", sa.String(128), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("immutable_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_operations_failure_signals_client_id"),
        "operations_failure_signals",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operations_failure_signals_signal_type"),
        "operations_failure_signals",
        ["signal_type"],
        unique=False,
    )

    op.create_table(
        "operations_failure_forecasts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("forecast_type", sa.String(64), nullable=False),
        sa.Column("forecast_window_minutes", sa.Integer(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("deterministic_version", sa.String(16), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("immutable_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_operations_failure_forecasts_client_id"),
        "operations_failure_forecasts",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operations_failure_forecasts_forecast_type"),
        "operations_failure_forecasts",
        ["forecast_type"],
        unique=False,
    )

    op.create_table(
        "operations_failure_risk_assessments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("forecast_id", sa.String(), nullable=True),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="low"),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_operations_failure_risk_assessments_client_id"),
        "operations_failure_risk_assessments",
        ["client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_operations_failure_risk_assessments_client_id"),
        table_name="operations_failure_risk_assessments",
    )
    op.drop_table("operations_failure_risk_assessments")
    op.drop_index(
        op.f("ix_operations_failure_forecasts_forecast_type"),
        table_name="operations_failure_forecasts",
    )
    op.drop_index(
        op.f("ix_operations_failure_forecasts_client_id"),
        table_name="operations_failure_forecasts",
    )
    op.drop_table("operations_failure_forecasts")
    op.drop_index(
        op.f("ix_operations_failure_signals_signal_type"),
        table_name="operations_failure_signals",
    )
    op.drop_index(
        op.f("ix_operations_failure_signals_client_id"),
        table_name="operations_failure_signals",
    )
    op.drop_table("operations_failure_signals")
