"""Phase 77 federation sync protocol migration stub.

Revision ID: phase77_federation_sync_protocol
Revises: phase76_attestation_framework
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "phase77_federation_sync_protocol"
down_revision = "phase76_attestation_framework"
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
    # sovereign_federation_environments, federation_synchronization_sessions, federation_lineage_links
    pass


def downgrade() -> None:
    pass
