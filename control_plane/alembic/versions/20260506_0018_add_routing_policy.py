"""add routing_policy

Revision ID: 20260506_0018
Revises: 20260505_0017
Create Date: 2026-05-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260506_0018'
down_revision = '20260505_0017'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('billing_plans', sa.Column('routing_policy_json', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('billing_plans', 'routing_policy_json')
