# Models: ConnectorOAuthClient, ConnectorOAuthToken, ConnectorCredentialGrant, ConnectorScopePolicy
"""connector oauth and credentials

Revision ID: 20260522_0094
Revises: 20260522_0093
Create Date: 2026-05-22 22:00:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260522_0094'
down_revision: Optional[str] = '20260522_0093'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. connector_oauth_clients
    op.create_table(
        'connector_oauth_clients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('connector_name', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=256), nullable=False),
        sa.Column('client_secret_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('auth_url', sa.String(length=512), nullable=False),
        sa.Column('token_url', sa.String(length=512), nullable=False),
        sa.Column('redirect_uri', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connector_oauth_clients_tenant_id'), 'connector_oauth_clients', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_connector_oauth_clients_connector_name'), 'connector_oauth_clients', ['connector_name'], unique=False)

    # 2. connector_oauth_tokens
    op.create_table(
        'connector_oauth_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['connector_oauth_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connector_oauth_tokens_tenant_id'), 'connector_oauth_tokens', ['tenant_id'], unique=False)

    # 3. connector_credential_grants
    op.create_table(
        'connector_credential_grants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('connector_name', sa.String(length=64), nullable=False),
        sa.Column('token_id', sa.UUID(), nullable=True),
        sa.Column('manual_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('grant_type', sa.String(length=32), nullable=False),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['token_id'], ['connector_oauth_tokens.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connector_credential_grants_tenant_id'), 'connector_credential_grants', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_connector_credential_grants_connector_name'), 'connector_credential_grants', ['connector_name'], unique=False)

    # 4. connector_scope_policies
    op.create_table(
        'connector_scope_policies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('connector_name', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('required_scopes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connector_scope_policies_tenant_id'), 'connector_scope_policies', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_connector_scope_policies_connector_name'), 'connector_scope_policies', ['connector_name'], unique=False)


def downgrade() -> None:
    op.drop_table('connector_scope_policies')
    op.drop_table('connector_credential_grants')
    op.drop_table('connector_oauth_tokens')
    op.drop_table('connector_oauth_clients')
