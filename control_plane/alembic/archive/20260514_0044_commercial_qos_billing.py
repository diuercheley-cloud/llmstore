"""commercial_qos_billing

Revision ID: 20260514_0044
Revises: 20260514_0043
Create Date: 2026-05-14 20:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260514_0044'
down_revision = '20260514_0043'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'commercial_qos_billing_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qos_tier', sa.String(length=32), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('chargeback_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('compute_seconds', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('priority_slots_consumed', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('estimated_internal_cost_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('opportunity_cost_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('billable_amount_brl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('billing_mode', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('wallet_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chargeback_id'], ['commercial_queue_chargebacks.id'], ),
        sa.ForeignKeyConstraint(['wallet_transaction_id'], ['ai_wallet_transactions.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_qos_billing_idempotency')
    )
    op.create_index(op.f('ix_commercial_qos_billing_records_client_id'), 'commercial_qos_billing_records', ['client_id'], unique=False)
    op.create_index(op.f('ix_commercial_qos_billing_records_qos_tier'), 'commercial_qos_billing_records', ['qos_tier'], unique=False)
    op.create_index(op.f('ix_commercial_qos_billing_records_model'), 'commercial_qos_billing_records', ['model'], unique=False)
    op.create_index(op.f('ix_commercial_qos_billing_records_period_start'), 'commercial_qos_billing_records', ['period_start'], unique=False)
    op.create_index(op.f('ix_commercial_qos_billing_records_period_end'), 'commercial_qos_billing_records', ['period_end'], unique=False)
    op.create_index(op.f('ix_commercial_qos_billing_records_status'), 'commercial_qos_billing_records', ['status'], unique=False)


def downgrade():
    op.drop_table('commercial_qos_billing_records')
