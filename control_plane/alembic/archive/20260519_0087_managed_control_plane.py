"""managed control plane base

Revision ID: 20260519_0087
Revises: 20260519_0086
Create Date: 2026-05-19 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260519_0087'
down_revision: Union[str, None] = '20260519_0086'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Managed Organizations
    op.create_table(
        'managed_organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_managed_organizations_slug'), 'managed_organizations', ['slug'], unique=True)

    # Managed Workspaces
    op.create_table(
        'managed_workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['managed_organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_managed_workspaces_slug'), 'managed_workspaces', ['slug'], unique=False)

    # Managed Appliances
    op.create_table(
        'managed_appliances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appliance_external_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='enrolled'),
        sa.Column('version', sa.String(length=64), nullable=True),
        sa.Column('health_status', sa.String(length=32), nullable=True),
        sa.Column('readiness', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('capacity_summary', sa.JSON(), nullable=True),
        sa.Column('enabled_providers', sa.JSON(), nullable=True),
        sa.Column('available_models', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['managed_workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('appliance_external_id')
    )
    op.create_index(op.f('ix_managed_appliances_appliance_external_id'), 'managed_appliances', ['appliance_external_id'], unique=True)

    # Appliance Enrollments
    op.create_table(
        'appliance_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrollment_token', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('used_by_appliance_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['used_by_appliance_id'], ['managed_appliances.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['managed_workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('enrollment_token')
    )
    op.create_index(op.f('ix_appliance_enrollments_enrollment_token'), 'appliance_enrollments', ['enrollment_token'], unique=True)

    # Appliance Heartbeats
    op.create_table(
        'appliance_heartbeats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appliance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('health_status', sa.String(length=32), nullable=False),
        sa.Column('readiness', sa.Boolean(), nullable=False),
        sa.Column('capacity_summary', sa.JSON(), nullable=False),
        sa.Column('enabled_providers', sa.JSON(), nullable=False),
        sa.Column('available_models', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['appliance_id'], ['managed_appliances.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Managed Billing Accounts
    op.create_table(
        'managed_billing_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('billing_email', sa.String(length=255), nullable=False),
        sa.Column('payment_method', sa.String(length=64), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('balance_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['managed_organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Managed Support Cases
    op.create_table(
        'managed_support_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('appliance_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='open'),
        sa.Column('priority', sa.String(length=32), nullable=False, server_default='medium'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['appliance_id'], ['managed_appliances.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['managed_organizations.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['managed_workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add organization_id to clients for isolation
    op.add_column('clients', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_clients_organization_id', 'clients', 'managed_organizations', ['organization_id'], ['id'])
    op.create_index(op.f('ix_clients_organization_id'), 'clients', ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clients_organization_id'), table_name='clients')
    op.drop_constraint('fk_clients_organization_id', 'clients', type_='foreignkey')
    op.drop_column('clients', 'organization_id')
    op.drop_table('managed_support_cases')
    op.drop_table('managed_billing_accounts')
    op.drop_table('appliance_heartbeats')
    op.drop_table('appliance_enrollments')
    op.drop_table('managed_appliances')
    op.drop_table('managed_workspaces')
    op.drop_table('managed_organizations')
