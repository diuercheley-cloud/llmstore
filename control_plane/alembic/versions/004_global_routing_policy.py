"""global routing policy

Revision ID: 004_global_routing_policy
Revises: 003_remediation_governance, phase80_plugin_supply_chain_provenance_sbom
Create Date: 2026-06-12 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_global_routing_policy'
down_revision = ('003_remediation_governance', 'phase80_plugin_supply_chain_provenance_sbom')
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'global_routing_policy_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('policy_json', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('previous_version_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('global_routing_policy_versions')
