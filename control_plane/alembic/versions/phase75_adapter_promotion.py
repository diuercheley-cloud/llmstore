"""Add Phase 75 Adapter Promotion models

Revision ID: phase75_adapter_promotion
Revises: e68f9a82dc48
Create Date: 2026-05-15 22:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase75_adapter_promotion'
down_revision = 'e68f9a82dc48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # adapter_promotion_workflows
    op.create_table(
        'adapter_promotion_workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('registry_entry_id', sa.UUID(), nullable=False),
        sa.Column('adapter_name', sa.String(length=100), nullable=False),
        sa.Column('adapter_version', sa.String(length=50), nullable=False),
        sa.Column('current_stage', sa.String(length=50), nullable=False),
        sa.Column('target_stage', sa.String(length=50), nullable=False),
        sa.Column('promotion_status', sa.String(length=50), nullable=False),
        sa.Column('deterministic_version', sa.String(length=50), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('immutable_hash', sa.String(length=64), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registry_entry_id'], ['signed_adapter_registry_entries.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_adapter_promotion_workflows_client_id'), 'adapter_promotion_workflows', ['client_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_workflows_registry_entry_id'), 'adapter_promotion_workflows', ['registry_entry_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_workflows_input_hash'), 'adapter_promotion_workflows', ['input_hash'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_workflows_immutable_hash'), 'adapter_promotion_workflows', ['immutable_hash'], unique=True)

    # adapter_promotion_gate_results
    op.create_table(
        'adapter_promotion_gate_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('gate_name', sa.String(length=100), nullable=False),
        sa.Column('gate_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('immutable_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['adapter_promotion_workflows.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_adapter_promotion_gate_results_client_id'), 'adapter_promotion_gate_results', ['client_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_gate_results_workflow_id'), 'adapter_promotion_gate_results', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_gate_results_immutable_hash'), 'adapter_promotion_gate_results', ['immutable_hash'], unique=True)

    # adapter_promotion_stage_transitions
    op.create_table(
        'adapter_promotion_stage_transitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('from_stage', sa.String(length=50), nullable=False),
        sa.Column('to_stage', sa.String(length=50), nullable=False),
        sa.Column('transition_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('immutable_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['adapter_promotion_workflows.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_adapter_promotion_stage_transitions_client_id'), 'adapter_promotion_stage_transitions', ['client_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_stage_transitions_workflow_id'), 'adapter_promotion_stage_transitions', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_stage_transitions_immutable_hash'), 'adapter_promotion_stage_transitions', ['immutable_hash'], unique=True)

    # adapter_promotion_receipts
    op.create_table(
        'adapter_promotion_receipts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('receipt_type', sa.String(length=100), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('immutable_hash', sa.String(length=64), nullable=False),
        sa.Column('signature_placeholder', sa.String(length=255), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['adapter_promotion_workflows.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_adapter_promotion_receipts_client_id'), 'adapter_promotion_receipts', ['client_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_receipts_workflow_id'), 'adapter_promotion_receipts', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_receipts_immutable_hash'), 'adapter_promotion_receipts', ['immutable_hash'], unique=True)

    # adapter_promotion_rollbacks
    op.create_table(
        'adapter_promotion_rollbacks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('from_stage', sa.String(length=50), nullable=False),
        sa.Column('rollback_to_stage', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('rollback_status', sa.String(length=50), nullable=False),
        sa.Column('immutable_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['adapter_promotion_workflows.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_adapter_promotion_rollbacks_client_id'), 'adapter_promotion_rollbacks', ['client_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_rollbacks_workflow_id'), 'adapter_promotion_rollbacks', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_adapter_promotion_rollbacks_immutable_hash'), 'adapter_promotion_rollbacks', ['immutable_hash'], unique=True)


def downgrade() -> None:
    op.drop_table('adapter_promotion_rollbacks')
    op.drop_table('adapter_promotion_receipts')
    op.drop_table('adapter_promotion_stage_transitions')
    op.drop_table('adapter_promotion_gate_results')
    op.drop_table('adapter_promotion_workflows')
