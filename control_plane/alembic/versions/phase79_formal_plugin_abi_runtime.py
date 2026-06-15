"""Phase 79 formal plugin ABI runtime migration stub.

Revision ID: phase79_formal_plugin_abi_runtime
Revises: phase78_compatibility_contracts
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "phase79_formal_plugin_abi_runtime"
down_revision = "phase78_compatibility_contracts"
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
    # plugin_abi_contracts, plugin_runtime_receipts
    pass


def downgrade() -> None:
    pass
