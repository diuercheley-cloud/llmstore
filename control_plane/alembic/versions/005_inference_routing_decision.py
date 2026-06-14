"""inference routing decision

Revision ID: 005_inference_routing_decision
Revises: 004_global_routing_policy
Create Date: 2026-06-12 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005_inference_routing_decision'
down_revision = '004_global_routing_policy'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'inference_routing_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('tenant_id', sa.String(length=100), nullable=True),
        sa.Column('client_id', sa.String(length=100), nullable=True),
        sa.Column('selected_backend', sa.String(length=100), nullable=True),
        sa.Column('selected_model', sa.String(length=100), nullable=False),
        sa.Column('candidate_backends', sa.JSON(), nullable=True),
        sa.Column('routing_policy_version', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('inference_routing_decisions')
