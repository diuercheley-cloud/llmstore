"""phase_21_capacity_planning

Revision ID: 3454d3bb899b
Revises: 
Create Date: 2026-05-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3454d3bb899b'
down_revision = '20260514_0041'
branch_labels = None
depends_on = None

def upgrade():
    # CommercialCapacitySnapshot
    op.create_table(
        'commercial_capacity_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cluster_id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('qos_tier', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('requests_per_minute', sa.Float(), nullable=True),
        sa.Column('concurrent_requests', sa.Integer(), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('queue_depth', sa.Integer(), nullable=True),
        sa.Column('gpu_utilization', sa.Float(), nullable=True),
        sa.Column('cpu_utilization', sa.Float(), nullable=True),
        sa.Column('memory_utilization', sa.Float(), nullable=True),
        sa.Column('estimated_tokens_per_second', sa.Float(), nullable=True),
        sa.Column('sla_violation_rate', sa.Float(), nullable=True),
        sa.Column('fallback_rate', sa.Float(), nullable=True),
        sa.Column('block_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_capacity_snapshots_cluster_id'), 'commercial_capacity_snapshots', ['cluster_id'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_snapshots_model'), 'commercial_capacity_snapshots', ['model'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_snapshots_node_id'), 'commercial_capacity_snapshots', ['node_id'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_snapshots_provider'), 'commercial_capacity_snapshots', ['provider'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_snapshots_qos_tier'), 'commercial_capacity_snapshots', ['qos_tier'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_snapshots_timestamp'), 'commercial_capacity_snapshots', ['timestamp'], unique=False)

    # CommercialCapacityForecast
    op.create_table(
        'commercial_capacity_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cluster_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('qos_tier', sa.String(), nullable=True),
        sa.Column('forecast_window_minutes', sa.Integer(), nullable=True),
        sa.Column('predicted_rpm', sa.Float(), nullable=True),
        sa.Column('predicted_concurrency', sa.Float(), nullable=True),
        sa.Column('predicted_latency_ms', sa.Float(), nullable=True),
        sa.Column('predicted_queue_depth', sa.Float(), nullable=True),
        sa.Column('predicted_sla_violation_rate', sa.Float(), nullable=True),
        sa.Column('predicted_capacity_exhaustion_at', sa.DateTime(), nullable=True),
        sa.Column('recommended_action', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_capacity_forecasts_cluster_id'), 'commercial_capacity_forecasts', ['cluster_id'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_forecasts_model'), 'commercial_capacity_forecasts', ['model'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_forecasts_provider'), 'commercial_capacity_forecasts', ['provider'], unique=False)
    op.create_index(op.f('ix_commercial_capacity_forecasts_qos_tier'), 'commercial_capacity_forecasts', ['qos_tier'], unique=False)

    # CommercialAutoscalingRecommendation
    op.create_table(
        'commercial_autoscaling_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cluster_id', sa.String(), nullable=False),
        sa.Column('recommendation_type', sa.String(), nullable=False),
        sa.Column('target_scope', sa.String(), nullable=False),
        sa.Column('target_identifier', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('predicted_sla_risk', sa.Float(), nullable=True),
        sa.Column('estimated_cost_impact_brl', sa.Float(), nullable=True),
        sa.Column('estimated_margin_impact_brl', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('dry_run_only', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_autoscaling_recommendations_cluster_id'), 'commercial_autoscaling_recommendations', ['cluster_id'], unique=False)
    op.create_index(op.f('ix_commercial_autoscaling_recommendations_recommendation_type'), 'commercial_autoscaling_recommendations', ['recommendation_type'], unique=False)
    op.create_index(op.f('ix_commercial_autoscaling_recommendations_target_identifier'), 'commercial_autoscaling_recommendations', ['target_identifier'], unique=False)
    op.create_index(op.f('ix_commercial_autoscaling_recommendations_target_scope'), 'commercial_autoscaling_recommendations', ['target_scope'], unique=False)


def downgrade():
    op.drop_table('commercial_autoscaling_recommendations')
    op.drop_table('commercial_capacity_forecasts')
    op.drop_table('commercial_capacity_snapshots')
