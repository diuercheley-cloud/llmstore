"""mcp oauth identity delegation tables

Revision ID: 20260528_0096
Revises: 20260528_0095
Create Date: 2026-05-28 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260528_0096'
down_revision: Union[str, Sequence[str], None] = '20260528_0095'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agent_mcp_oauth import (
        AgentMCPDelegatedGrant,
        AgentMCPOAuthClient,
        AgentMCPScopePolicy,
        AgentMCPTokenExchange,
    )
    bind = op.get_bind()
    tables = [
        AgentMCPOAuthClient.__table__,
        AgentMCPDelegatedGrant.__table__,
        AgentMCPTokenExchange.__table__,
        AgentMCPScopePolicy.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_mcp_scope_policies')
    op.drop_table('agent_mcp_token_exchanges')
    op.drop_table('agent_mcp_delegated_grants')
    op.drop_table('agent_mcp_oauth_clients')
