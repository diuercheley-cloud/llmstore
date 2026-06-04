"""Add model runtime instances

Revision ID: 3e1d04ffb6d5
Revises: ded3a7f9843c
Create Date: 2024-05-18 17:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3e1d04ffb6d5'
down_revision: Union[str, None] = 'ded3a7f9843c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('model_runtime_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('backend_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_path', sa.String(length=1024), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('health_status', sa.String(length=32), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['backend_id'], ['inference_backends.id'], ),
        sa.ForeignKeyConstraint(['model_id'], ['model_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_runtime_instances_backend_id'), 'model_runtime_instances', ['backend_id'], unique=False)
    op.create_index(op.f('ix_model_runtime_instances_is_active'), 'model_runtime_instances', ['is_active'], unique=False)
    op.create_index(op.f('ix_model_runtime_instances_model_id'), 'model_runtime_instances', ['model_id'], unique=False)


def downgrade() -> None:
    op.drop_table('model_runtime_instances')
