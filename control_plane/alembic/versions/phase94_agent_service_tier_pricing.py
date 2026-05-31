"""add_agent_service_tier_pricing

Revision ID: phase94_agent_service_tier_pricing
Revises: phase93_agent_optimization
Create Date: 2026-05-30 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase94_agent_service_tier_pricing"
down_revision = "phase93_agent_optimization"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_service_tiers", sa.Column("price_per_run_brl", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("agent_service_tiers", sa.Column("price_per_1k_tokens_brl", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("agent_service_tiers", sa.Column("monthly_fee_brl", sa.Float(), server_default="0.0", nullable=False))

    # Seed default tiers with pricing
    op.execute(
        """
        INSERT INTO agent_service_tiers (id, name, rate_limit_per_minute, monthly_run_limit, price_per_run_brl, price_per_1k_tokens_brl, monthly_fee_brl, features, created_at)
        VALUES
            (gen_random_uuid(), 'free', 10, 100, 0.0, 0.0, 0.0, '{}'::jsonb, NOW()),
            (gen_random_uuid(), 'pro', 60, 10000, 0.01, 0.02, 29.0, '{"sync_mode": true}'::jsonb, NOW()),
            (gen_random_uuid(), 'enterprise', 300, 100000, 0.005, 0.01, 99.0, '{"sync_mode": true, "webhook_custom_headers": true}'::jsonb, NOW())
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade():
    op.drop_column("agent_service_tiers", "price_per_run_brl")
    op.drop_column("agent_service_tiers", "price_per_1k_tokens_brl")
    op.drop_column("agent_service_tiers", "monthly_fee_brl")
