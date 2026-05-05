"""rag limits usage

Revision ID: 20260505_0017
Revises: 20260505_0016
Create Date: 2026-05-05 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260505_0017'
down_revision = '20260505_0016'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add columns to billing_plans
    op.add_column('billing_plans', sa.Column('rag_max_documents', sa.Integer(), nullable=True))
    op.add_column('billing_plans', sa.Column('rag_max_storage_mb', sa.Integer(), nullable=True))
    op.add_column('billing_plans', sa.Column('rag_max_pages_per_month', sa.Integer(), nullable=True))
    op.add_column('billing_plans', sa.Column('rag_max_queries_per_month', sa.Integer(), nullable=True))

    # Table client_feature_blocks
    op.create_table(
        'client_feature_blocks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('feature', sa.String(length=50), nullable=False),
        sa.Column('blocked', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by_role', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_client_feature_blocks_client_id'), 'client_feature_blocks', ['client_id'], unique=False)
    op.create_index(op.f('ix_client_feature_blocks_feature'), 'client_feature_blocks', ['feature'], unique=False)

    # Table rag_usage_events
    op.create_table(
        'rag_usage_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('tokens', sa.Integer(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rag_usage_events_client_id'), 'rag_usage_events', ['client_id'], unique=False)
    op.create_index(op.f('ix_rag_usage_events_created_at'), 'rag_usage_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_rag_usage_events_event_type'), 'rag_usage_events', ['event_type'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_rag_usage_events_event_type'), table_name='rag_usage_events')
    op.drop_index(op.f('ix_rag_usage_events_created_at'), table_name='rag_usage_events')
    op.drop_index(op.f('ix_rag_usage_events_client_id'), table_name='rag_usage_events')
    op.drop_table('rag_usage_events')
    op.drop_index(op.f('ix_client_feature_blocks_feature'), table_name='client_feature_blocks')
    op.drop_index(op.f('ix_client_feature_blocks_client_id'), table_name='client_feature_blocks')
    op.drop_table('client_feature_blocks')
    op.drop_column('billing_plans', 'rag_max_queries_per_month')
    op.drop_column('billing_plans', 'rag_max_pages_per_month')
    op.drop_column('billing_plans', 'rag_max_storage_mb')
    op.drop_column('billing_plans', 'rag_max_documents')
