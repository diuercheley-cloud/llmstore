"""phase_21_1_infra_simulation

Revision ID: f899d30584c3
Revises: 3454d3bb899b
Create Date: 2026-05-14 11:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f899d30584c3'
down_revision = '3454d3bb899b'
branch_labels = None
depends_on = None

def upgrade():
    # CommercialInfrastructureSimulation
    op.create_table(
        'commercial_infra_simulations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_type', sa.String(), nullable=False),
        sa.Column('target_scope', sa.String(), nullable=False),
        sa.Column('target_identifier', sa.String(), nullable=False),
        sa.Column('requested_action_json', sa.JSON(), nullable=False),
        sa.Column('predicted_capacity_impact_json', sa.JSON(), nullable=True),
        sa.Column('predicted_cost_impact_brl', sa.Float(), nullable=True),
        sa.Column('predicted_margin_impact_brl', sa.Float(), nullable=True),
        sa.Column('predicted_sla_impact_json', sa.JSON(), nullable=True),
        sa.Column('predicted_queue_impact_json', sa.JSON(), nullable=True),
        sa.Column('predicted_latency_impact_json', sa.JSON(), nullable=True),
        sa.Column('blast_radius', sa.String(), nullable=True),
        sa.Column('safety_gate_status', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_infra_simulations_simulation_type'), 'commercial_infra_simulations', ['simulation_type'], unique=False)
    op.create_index(op.f('ix_commercial_infra_simulations_target_scope'), 'commercial_infra_simulations', ['target_scope'], unique=False)
    op.create_index(op.f('ix_commercial_infra_simulations_target_identifier'), 'commercial_infra_simulations', ['target_identifier'], unique=False)
    op.create_index(op.f('ix_commercial_infra_simulations_blast_radius'), 'commercial_infra_simulations', ['blast_radius'], unique=False)
    op.create_index(op.f('ix_commercial_infra_simulations_safety_gate_status'), 'commercial_infra_simulations', ['safety_gate_status'], unique=False)

    # CommercialSafetyPolicy
    op.create_table(
        'commercial_safety_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('max_predicted_cost_increase_percent', sa.Float(), nullable=True),
        sa.Column('max_predicted_margin_drop_percent', sa.Float(), nullable=True),
        sa.Column('max_predicted_sla_violation_percent', sa.Float(), nullable=True),
        sa.Column('max_nodes_affected', sa.Integer(), nullable=True),
        sa.Column('max_clusters_affected', sa.Integer(), nullable=True),
        sa.Column('require_manual_approval_above_blast_radius', sa.String(), nullable=True),
        sa.Column('allow_scale_down', sa.Boolean(), nullable=True),
        sa.Column('allow_scale_up', sa.Boolean(), nullable=True),
        sa.Column('allow_cluster_failover', sa.Boolean(), nullable=True),
        sa.Column('allow_cross_region_routing', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_safety_policies_policy_name'), 'commercial_safety_policies', ['policy_name'], unique=True)

    # CommercialApprovalRecord
    op.create_table(
        'commercial_approval_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('approver', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['commercial_infra_simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_approval_records_simulation_id'), 'commercial_approval_records', ['simulation_id'], unique=False)
    op.create_index(op.f('ix_commercial_approval_records_status'), 'commercial_approval_records', ['status'], unique=False)


def downgrade():
    op.drop_table('commercial_approval_records')
    op.drop_table('commercial_safety_policies')
    op.drop_table('commercial_infra_simulations')
