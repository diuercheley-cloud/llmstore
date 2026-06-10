"""qos_priority_queue

Revision ID: 20260514_0042
Revises: 8a6cd3ddb494
Create Date: 2026-05-14 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '20260514_0042'
down_revision = '8a6cd3ddb494'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('generation_jobs', sa.Column('qos_tier', sa.String(length=32), nullable=True))
    op.add_column('generation_jobs', sa.Column('effective_priority', sa.Numeric(precision=20, scale=6), nullable=True))
    op.add_column('generation_jobs', sa.Column('dequeued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('generation_jobs', sa.Column('queue_wait_ms', sa.Integer(), nullable=True))
    op.add_column('generation_jobs', sa.Column('rate_limit_status', sa.String(length=32), nullable=True))
    op.add_column('generation_jobs', sa.Column('rate_limit_reason', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('generation_jobs', 'rate_limit_reason')
    op.drop_column('generation_jobs', 'rate_limit_status')
    op.drop_column('generation_jobs', 'queue_wait_ms')
    op.drop_column('generation_jobs', 'dequeued_at')
    op.drop_column('generation_jobs', 'effective_priority')
    op.drop_column('generation_jobs', 'qos_tier')
