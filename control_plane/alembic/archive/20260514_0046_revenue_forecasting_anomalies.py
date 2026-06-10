"""revenue_forecasting_anomalies

Revision ID: 20260514_0046
Revises: 20260514_0045
Create Date: 2026-05-14 22:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260514_0046'
down_revision = '20260514_0045'
branch_labels = None
depends_on = None


def upgrade():
    # commercial_revenue_forecasts
    op.create_table(
        'commercial_revenue_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('forecast_type', sa.String(length=32), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('qos_tier', sa.String(length=32), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_window_days', sa.Integer(), nullable=False),
        sa.Column('predicted_amount_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('lower_bound_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('upper_bound_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('confidence', sa.String(length=16), nullable=False),
        sa.Column('method', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_revenue_forecasts_forecast_type'), 'commercial_revenue_forecasts', ['forecast_type'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_client_id'), 'commercial_revenue_forecasts', ['client_id'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_qos_tier'), 'commercial_revenue_forecasts', ['qos_tier'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_provider'), 'commercial_revenue_forecasts', ['provider'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_model'), 'commercial_revenue_forecasts', ['model'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_period_start'), 'commercial_revenue_forecasts', ['period_start'], unique=False)
    op.create_index(op.f('ix_commercial_revenue_forecasts_period_end'), 'commercial_revenue_forecasts', ['period_end'], unique=False)

    # commercial_financial_anomalies
    op.create_table(
        'commercial_financial_anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('anomaly_type', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observed_value_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('expected_value_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('deviation_percent', sa.Float(), nullable=False),
        sa.Column('z_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_financial_anomalies_anomaly_type'), 'commercial_financial_anomalies', ['anomaly_type'], unique=False)
    op.create_index(op.f('ix_commercial_financial_anomalies_severity'), 'commercial_financial_anomalies', ['severity'], unique=False)
    op.create_index(op.f('ix_commercial_financial_anomalies_client_id'), 'commercial_financial_anomalies', ['client_id'], unique=False)
    op.create_index(op.f('ix_commercial_financial_anomalies_detected_at'), 'commercial_financial_anomalies', ['detected_at'], unique=False)
    op.create_index(op.f('ix_commercial_financial_anomalies_status'), 'commercial_financial_anomalies', ['status'], unique=False)


def downgrade():
    op.drop_table('commercial_financial_anomalies')
    op.drop_table('commercial_revenue_forecasts')
