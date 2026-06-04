"""add tokenizer info to usage records

Revision ID: 20260518_0084
Revises: 20260518_0083
Create Date: 2026-05-18 14:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_0084"
down_revision = "20260518_0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('usage_records', sa.Column('token_count_method', sa.String(length=32), nullable=True))
    op.add_column('usage_records', sa.Column('tokens_estimated', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('request_financials', sa.Column('token_count_method', sa.String(length=32), nullable=True))
    op.add_column('request_financials', sa.Column('tokens_estimated', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('generation_jobs', sa.Column('token_count_method', sa.String(length=32), nullable=True))
    op.add_column('generation_jobs', sa.Column('tokens_estimated', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('generation_jobs', 'tokens_estimated')
    op.drop_column('generation_jobs', 'token_count_method')
    op.drop_column('request_financials', 'tokens_estimated')
    op.drop_column('request_financials', 'token_count_method')
    op.drop_column('usage_records', 'tokens_estimated')
    op.drop_column('usage_records', 'token_count_method')
