"""queue_fairness_chargeback

Revision ID: 20260514_0043
Revises: 20260514_0042
Create Date: 2026-05-14 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260514_0043'
down_revision = '20260514_0042'
branch_labels = None
depends_on = None


def upgrade():
    # CommercialQueueMetric
    op.create_table(
        'commercial_queue_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('qos_tier', sa.String(length=32), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('queue_depth', sa.Integer(), nullable=False),
        sa.Column('avg_wait_ms', sa.Integer(), nullable=False),
        sa.Column('p95_wait_ms', sa.Integer(), nullable=False),
        sa.Column('max_wait_ms', sa.Integer(), nullable=False),
        sa.Column('jobs_processed', sa.Integer(), nullable=False),
        sa.Column('jobs_throttled', sa.Integer(), nullable=False),
        sa.Column('starvation_count', sa.Integer(), nullable=False),
        sa.Column('sla_queue_violations', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_queue_metrics_timestamp'), 'commercial_queue_metrics', ['timestamp'], unique=False)
    op.create_index(op.f('ix_commercial_queue_metrics_qos_tier'), 'commercial_queue_metrics', ['qos_tier'], unique=False)
    op.create_index(op.f('ix_commercial_queue_metrics_client_id'), 'commercial_queue_metrics', ['client_id'], unique=False)
    op.create_index(op.f('ix_commercial_queue_metrics_model'), 'commercial_queue_metrics', ['model'], unique=False)

    # CommercialQueueChargeback
    op.create_table(
        'commercial_queue_chargebacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('qos_tier', sa.String(length=32), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('compute_seconds', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('queue_wait_seconds', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('priority_slots_consumed', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('estimated_opportunity_cost_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('estimated_internal_cost_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('chargeback_amount_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_queue_chargebacks_period_start'), 'commercial_queue_chargebacks', ['period_start'], unique=False)
    op.create_index(op.f('ix_commercial_queue_chargebacks_period_end'), 'commercial_queue_chargebacks', ['period_end'], unique=False)
    op.create_index(op.f('ix_commercial_queue_chargebacks_qos_tier'), 'commercial_queue_chargebacks', ['qos_tier'], unique=False)
    op.create_index(op.f('ix_commercial_queue_chargebacks_client_id'), 'commercial_queue_chargebacks', ['client_id'], unique=False)
    op.create_index(op.f('ix_commercial_queue_chargebacks_model'), 'commercial_queue_chargebacks', ['model'], unique=False)


def downgrade():
    op.drop_table('commercial_queue_chargebacks')
    op.drop_table('commercial_queue_metrics')
