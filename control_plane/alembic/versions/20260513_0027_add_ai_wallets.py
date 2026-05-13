"""add_ai_wallets_and_transactions

Revision ID: 20260513_0027
Revises: c93fcfd07a5d
Create Date: 2026-05-13 08:00:00.000000
"""
from alembic import op
import sqlalchemy as sa



revision = '20260513_0027'
down_revision = 'c93fcfd07a5d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('ai_wallets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('balance_brl', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('reserved_brl', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id')
    )
    op.create_index(op.f('ix_ai_wallets_client_id'), 'ai_wallets', ['client_id'], unique=True)
    op.create_index(op.f('ix_ai_wallets_status'), 'ai_wallets', ['status'], unique=False)

    op.create_table('ai_wallet_transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('wallet_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=24), nullable=False),
        sa.Column('amount_brl', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('balance_after_brl', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('reference_type', sa.String(length=64), nullable=True),
        sa.Column('reference_id', sa.String(length=128), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wallet_id'], ['ai_wallets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_wallet_tx_idempotency')
    )
    op.create_index(op.f('ix_ai_wallet_transactions_client_id'), 'ai_wallet_transactions', ['client_id'], unique=False)
    op.create_index(op.f('ix_ai_wallet_transactions_type'), 'ai_wallet_transactions', ['type'], unique=False)
    op.create_index(op.f('ix_ai_wallet_transactions_created_at'), 'ai_wallet_transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_wallet_transactions_wallet_id'), 'ai_wallet_transactions', ['wallet_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_wallet_transactions_wallet_id'), table_name='ai_wallet_transactions')
    op.drop_index(op.f('ix_ai_wallet_transactions_created_at'), table_name='ai_wallet_transactions')
    op.drop_index(op.f('ix_ai_wallet_transactions_type'), table_name='ai_wallet_transactions')
    op.drop_index(op.f('ix_ai_wallet_transactions_client_id'), table_name='ai_wallet_transactions')
    op.drop_table('ai_wallet_transactions')
    op.drop_index(op.f('ix_ai_wallets_status'), table_name='ai_wallets')
    op.drop_index(op.f('ix_ai_wallets_client_id'), table_name='ai_wallets')
    op.drop_table('ai_wallets')
