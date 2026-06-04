"""agent iam tables

Revision ID: phase92_agent_iam
Revises: phase91_agent_event_driven
Create Date: 2026-05-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'phase92_agent_iam'
down_revision: Union[str, Sequence[str], None] = 'phase91_agent_event_driven'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agent_iam import (
        AgentCredentialAuditEvent,
        AgentDelegatedToken,
        AgentIdentityBinding,
        AgentScopePolicy,
        AgentServicePrincipal,
        AgentTokenGrant,
    )
    bind = op.get_bind()
    tables = [
        AgentServicePrincipal.__table__,
        AgentDelegatedToken.__table__,
        AgentTokenGrant.__table__,
        AgentScopePolicy.__table__,
        AgentCredentialAuditEvent.__table__,
        AgentIdentityBinding.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_identity_bindings')
    op.drop_table('agent_credential_audit_events')
    op.drop_table('agent_scope_policies')
    op.drop_table('agent_token_grants')
    op.drop_table('agent_delegated_tokens')
    op.drop_table('agent_service_principals')
