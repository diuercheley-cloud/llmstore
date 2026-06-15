"""Phase 76 attestation framework migration stub.

Revision ID: phase76_attestation_framework
Revises: 004_global_routing_policy
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "phase76_attestation_framework"
down_revision = "004_global_routing_policy"
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
    # sovereign_execution_attestations, attestation_trust_policies, attestation_federation_bundles
    pass


def downgrade() -> None:
    pass
