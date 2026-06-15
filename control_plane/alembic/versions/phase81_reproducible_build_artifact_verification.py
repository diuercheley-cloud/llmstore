"""Phase 81 reproducible build artifact verification migration stub.

Revision ID: phase81_reproducible_build_artifact_verification
Revises: phase80_plugin_supply_chain_provenance_sbom
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "phase81_reproducible_build_artifact_verification"
down_revision = "phase80_plugin_supply_chain_provenance_sbom"
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
    # reproducible_build_manifests, artifact_verification_records, _uuid_type
    pass


def downgrade() -> None:
    pass
