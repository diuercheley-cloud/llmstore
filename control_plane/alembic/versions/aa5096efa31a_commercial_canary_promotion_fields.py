"""commercial_canary_promotion_fields

Revision ID: aa5096efa31a
Revises: 20260514_0033
Create Date: 2026-05-14 12:51:08.435923
"""
from alembic import op
import sqlalchemy as sa



revision = 'aa5096efa31a'
down_revision = '20260514_0033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CommercialRoutingConfig fields
    op.add_column('commercial_routing_config', sa.Column('canary_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_last_promoted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_current_step', sa.Integer(), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_target_step', sa.Integer(), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_observation_window_minutes', sa.Integer(), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_promotion_status', sa.String(length=50), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('canary_failure_reason', sa.Text(), nullable=True))
    op.add_column('commercial_routing_config', sa.Column('stable_promoted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_commercial_routing_config_canary_promotion_status'), 'commercial_routing_config', ['canary_promotion_status'], unique=False)

    # CommercialRoutingEvent fields
    op.add_column('commercial_routing_events', sa.Column('commercial_config_id', sa.UUID(), nullable=True))
    op.add_column('commercial_routing_events', sa.Column('commercial_config_variant', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_commercial_routing_events_commercial_config_id'), 'commercial_routing_events', ['commercial_config_id'], unique=False)
    op.create_index(op.f('ix_commercial_routing_events_commercial_config_variant'), 'commercial_routing_events', ['commercial_config_variant'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_commercial_routing_events_commercial_config_variant'), table_name='commercial_routing_events')
    op.drop_index(op.f('ix_commercial_routing_events_commercial_config_id'), table_name='commercial_routing_events')
    op.drop_column('commercial_routing_events', 'commercial_config_variant')
    op.drop_column('commercial_routing_events', 'commercial_config_id')
    
    op.drop_index(op.f('ix_commercial_routing_config_canary_promotion_status'), table_name='commercial_routing_config')
    op.drop_column('commercial_routing_config', 'stable_promoted_at')
    op.drop_column('commercial_routing_config', 'canary_failure_reason')
    op.drop_column('commercial_routing_config', 'canary_promotion_status')
    op.drop_column('commercial_routing_config', 'canary_observation_window_minutes')
    op.drop_column('commercial_routing_config', 'canary_target_step')
    op.drop_column('commercial_routing_config', 'canary_current_step')
    op.drop_column('commercial_routing_config', 'canary_last_promoted_at')
    op.drop_column('commercial_routing_config', 'canary_started_at')
