"""phase46_public_attestation_gateway

Revision ID: f637b1293c40
Revises: e526a1282b29
Create Date: 2026-05-15 13:12:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f637b1293c40"
down_revision = "e526a1282b29"
branch_labels = None
depends_on = None


def upgrade():
    # 1. CommercialPublicAttestationRequest
    op.create_table(
        "commercial_public_attestation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("submitted_proof_hash", sa.String(length=128), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_public_attestation_requests_request_hash"),
        "commercial_public_attestation_requests",
        ["request_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_public_attestation_requests_submitted_proof_hash"),
        "commercial_public_attestation_requests",
        ["submitted_proof_hash"],
        unique=False,
    )

    # 2. CommercialPublicAttestationResult
    op.create_table(
        "commercial_public_attestation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verification_type", sa.String(length=50), nullable=False),
        sa.Column("result", sa.String(length=50), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["commercial_public_attestation_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("commercial_public_attestation_results")
    op.drop_index(
        op.f("ix_commercial_public_attestation_requests_submitted_proof_hash"),
        table_name="commercial_public_attestation_requests",
    )
    op.drop_index(
        op.f("ix_commercial_public_attestation_requests_request_hash"),
        table_name="commercial_public_attestation_requests",
    )
    op.drop_table("commercial_public_attestation_requests")
