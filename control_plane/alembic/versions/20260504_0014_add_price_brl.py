"""add price_brl

Revision ID: 20260504_0014
Revises: e96571d94193
Create Date: 2026-05-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260504_0014'
down_revision = 'e96571d94193'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('billing_plans', sa.Column('price_brl', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))

def downgrade() -> None:
    op.drop_column('billing_plans', 'price_brl')
