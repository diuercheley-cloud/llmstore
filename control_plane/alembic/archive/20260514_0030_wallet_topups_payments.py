"""add wallet topup intents and payment webhook events

Revision ID: 20260514_0030
Revises: 20260514_0029
Create Date: 2026-05-14 00:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0030"
down_revision = "20260514_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_topup_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_brl", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payment_data_json", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_wallet_topup_provider_external_id"),
        sa.UniqueConstraint("provider", "idempotency_key", name="uq_wallet_topup_provider_idempotency_key"),
    )
    op.create_index("ix_wallet_topup_intents_client_id", "wallet_topup_intents", ["client_id"])
    op.create_index("ix_wallet_topup_intents_status", "wallet_topup_intents", ["status"])
    op.create_index("ix_wallet_topup_intents_provider", "wallet_topup_intents", ["provider"])
    op.create_index("ix_wallet_topup_intents_external_id", "wallet_topup_intents", ["external_id"])
    op.create_index("ix_wallet_topup_intents_idempotency_key", "wallet_topup_intents", ["idempotency_key"])
    op.create_index("ix_wallet_topup_intents_created_at", "wallet_topup_intents", ["created_at"])

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topup_intent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_brl", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_summary_json", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topup_intent_id"], ["wallet_topup_intents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_payment_webhook_provider_external_id"),
        sa.UniqueConstraint("provider", "idempotency_key", name="uq_payment_webhook_provider_idempotency_key"),
    )
    op.create_index("ix_payment_webhook_events_client_id", "payment_webhook_events", ["client_id"])
    op.create_index("ix_payment_webhook_events_topup_intent_id", "payment_webhook_events", ["topup_intent_id"])
    op.create_index("ix_payment_webhook_events_status", "payment_webhook_events", ["status"])
    op.create_index("ix_payment_webhook_events_provider", "payment_webhook_events", ["provider"])
    op.create_index("ix_payment_webhook_events_external_id", "payment_webhook_events", ["external_id"])
    op.create_index("ix_payment_webhook_events_idempotency_key", "payment_webhook_events", ["idempotency_key"])
    op.create_index("ix_payment_webhook_events_created_at", "payment_webhook_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_created_at", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_idempotency_key", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_external_id", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_provider", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_status", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_topup_intent_id", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_client_id", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")

    op.drop_index("ix_wallet_topup_intents_created_at", table_name="wallet_topup_intents")
    op.drop_index("ix_wallet_topup_intents_idempotency_key", table_name="wallet_topup_intents")
    op.drop_index("ix_wallet_topup_intents_external_id", table_name="wallet_topup_intents")
    op.drop_index("ix_wallet_topup_intents_provider", table_name="wallet_topup_intents")
    op.drop_index("ix_wallet_topup_intents_status", table_name="wallet_topup_intents")
    op.drop_index("ix_wallet_topup_intents_client_id", table_name="wallet_topup_intents")
    op.drop_table("wallet_topup_intents")
