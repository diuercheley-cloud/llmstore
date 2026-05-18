"""Add PKI, Attestation, and Plugin models

Revision ID: 67c7f972d70b
Revises: 20260518_0084
Create Date: 2026-05-18 16:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '67c7f972d70b'
down_revision: Union[str, None] = '20260518_0084'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('certificate_inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('issuer', sa.String(length=255), nullable=False),
        sa.Column('serial_number', sa.String(length=255), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pem_cert', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_certificate_inventory_subject'), 'certificate_inventory', ['subject'], unique=False)
    op.create_index(op.f('ix_certificate_inventory_issuer'), 'certificate_inventory', ['issuer'], unique=False)
    op.create_index(op.f('ix_certificate_inventory_serial_number'), 'certificate_inventory', ['serial_number'], unique=True)
    op.create_index(op.f('ix_certificate_inventory_valid_until'), 'certificate_inventory', ['valid_until'], unique=False)
    op.create_index(op.f('ix_certificate_inventory_is_revoked'), 'certificate_inventory', ['is_revoked'], unique=False)

    op.create_table('attestation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('measurements_json', sa.Text(), nullable=False),
        sa.Column('policy_result', sa.String(length=64), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('certificate_chain', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attestation_reports_client_id'), 'attestation_reports', ['client_id'], unique=False)
    op.create_index(op.f('ix_attestation_reports_timestamp'), 'attestation_reports', ['timestamp'], unique=False)
    op.create_index(op.f('ix_attestation_reports_policy_result'), 'attestation_reports', ['policy_result'], unique=False)

    op.create_table('plugin_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('entrypoint', sa.String(length=255), nullable=False),
        sa.Column('permissions_json', sa.Text(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('load_error', sa.Text(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plugin_registry_name'), 'plugin_registry', ['name'], unique=False)
    op.create_index(op.f('ix_plugin_registry_sha256'), 'plugin_registry', ['sha256'], unique=False)
    op.create_index(op.f('ix_plugin_registry_is_active'), 'plugin_registry', ['is_active'], unique=False)

def downgrade() -> None:
    op.drop_table('plugin_registry')
    op.drop_table('attestation_reports')
    op.drop_table('certificate_inventory')
