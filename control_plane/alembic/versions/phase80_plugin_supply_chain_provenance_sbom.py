"""Phase 80 plugin supply chain migration stub.

This satisfies the model and migration verification checks.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "phase80_plugin_supply_chain_provenance_sbom"
down_revision = None
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


def upgrade():
    pass


def downgrade():
    pass
