"""Phase 41 Cryptographic Inference Receipts + Non-Repudiation

Revision ID: 20260515_0059
Revises: 20260515_0058
Create Date: 2026-05-15 03:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_0059"
down_revision = "20260515_0058"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_inference_receipts",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("reproducibility_record_id", _uuid_type(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("backend_name", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("prompt_hash", sa.String(length=128), nullable=False),
        sa.Column("response_hash", sa.String(length=128), nullable=False),
        sa.Column("request_payload_hash", sa.String(length=128), nullable=True),
        sa.Column("response_payload_hash", sa.String(length=128), nullable=True),
        sa.Column("runtime_snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("routing_decision_hash", sa.String(length=128), nullable=True),
        sa.Column("receipt_hash", sa.String(length=128), nullable=False),
        sa.Column("previous_receipt_hash", sa.String(length=128), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("detached_signature", sa.Text(), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("timestamp_mode", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("timestamp_token", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "verification_status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("tamper_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reproducibility_record_id"],
            ["commercial_inference_reproducibility_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_hash"),
    )
    op.create_index(
        "ix_commercial_inference_receipts_receipt_hash",
        "commercial_inference_receipts",
        ["receipt_hash"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_client_id",
        "commercial_inference_receipts",
        ["client_id"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_verification_status",
        "commercial_inference_receipts",
        ["verification_status"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_runtime_snapshot_hash",
        "commercial_inference_receipts",
        ["runtime_snapshot_hash"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_routing_decision_hash",
        "commercial_inference_receipts",
        ["routing_decision_hash"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_previous_receipt_hash",
        "commercial_inference_receipts",
        ["previous_receipt_hash"],
    )
    op.create_index(
        "ix_commercial_inference_receipts_immutable_hash",
        "commercial_inference_receipts",
        ["immutable_hash"],
    )

    op.create_table(
        "commercial_inference_receipt_ledger_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("receipt_id", _uuid_type(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["commercial_inference_receipts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_inf_receipt_le_rid",
        "commercial_inference_receipt_ledger_events",
        ["receipt_id"],
    )
    op.create_index(
        "ix_comm_inf_receipt_le_etype",
        "commercial_inference_receipt_ledger_events",
        ["event_type"],
    )

    op.create_table(
        "commercial_inference_receipt_verification_reports",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("receipt_id", _uuid_type(), nullable=False),
        sa.Column("verification_result", sa.String(length=16), nullable=False),
        sa.Column("chain_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("signature_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timestamp_valid", sa.Boolean(), nullable=True),
        sa.Column("runtime_match", sa.Boolean(), nullable=True),
        sa.Column("replay_match", sa.Boolean(), nullable=True),
        sa.Column("drift_detected", sa.Boolean(), nullable=True),
        sa.Column("report_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["commercial_inference_receipts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_inf_receipt_vr_rid",
        "commercial_inference_receipt_verification_reports",
        ["receipt_id"],
    )
    op.create_index(
        "ix_comm_inf_receipt_vr_res",
        "commercial_inference_receipt_verification_reports",
        ["verification_result"],
    )


def downgrade() -> None:
    op.drop_table("commercial_inference_receipt_verification_reports")
    op.drop_table("commercial_inference_receipt_ledger_events")
    op.drop_table("commercial_inference_receipts")
