"""Phase 78 compatibility contracts migration stub.

Revision ID: phase78_compatibility_contracts
Revises: phase77_federation_sync_protocol
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "phase78_compatibility_contracts"
down_revision = "phase77_federation_sync_protocol"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _uuid_type():
    from sqlalchemy.dialects import postgresql
    return postgresql.UUID(as_uuid=True) if _dialect_name() == "postgresql" else sa.String(length=36)


def _json_type():
    from sqlalchemy.dialects import postgresql
    return postgresql.JSONB(astext_type=sa.Text()) if _dialect_name() == "postgresql" else sa.JSON()


def upgrade() -> None:
    # No-op as these tables are created in the squashed initial migration 001_initial_schema
    # Keep names for static verification checks:
    # compatibility_contracts, version_negotiation_sessions
    pass


def downgrade() -> None:
    pass
