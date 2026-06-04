"""client soft delete

Revision ID: 20260502_0013
Revises: 20260430_0012
Create Date: 2026-05-02 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260502_0013'
down_revision = '20260430_0012'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clients', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('clients', 'deleted_at')
