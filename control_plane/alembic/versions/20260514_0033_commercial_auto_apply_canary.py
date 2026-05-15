"""commercial auto apply canary

Revision ID: 20260514_0033
Revises: 20260514_0032
Create Date: 2026-05-14 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0033"
down_revision = "20260514_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("commercial_routing_config", sa.Column("canary_percent", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("commercial_routing_config", sa.Column("canary_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("commercial_routing_config", sa.Column("auto_applied", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("commercial_routing_config", sa.Column("can_auto_apply", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("commercial_routing_config", sa.Column("auto_apply_reason", sa.String(length=255), nullable=True))
    op.add_column("commercial_routing_config", sa.Column("auto_apply_source_event_count", sa.Integer(), nullable=True))
    op.add_column("commercial_routing_config", sa.Column("auto_apply_confidence", sa.String(length=50), nullable=True))
    op.add_column("commercial_routing_config", sa.Column("promoted_from_config_id", sa.UUID(), nullable=True))
    op.add_column("commercial_routing_config", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_commercial_routing_config_canary_lookup", "commercial_routing_config", ["provider", "model", "canary_enabled"])
    op.create_index("ix_commercial_routing_config_auto_applied", "commercial_routing_config", ["auto_applied"])
    op.create_index("ix_commercial_routing_config_expires_at", "commercial_routing_config", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_commercial_routing_config_expires_at", table_name="commercial_routing_config")
    op.drop_index("ix_commercial_routing_config_auto_applied", table_name="commercial_routing_config")
    op.drop_index("ix_commercial_routing_config_canary_lookup", table_name="commercial_routing_config")
    
    op.drop_column("commercial_routing_config", "expires_at")
    op.drop_column("commercial_routing_config", "promoted_from_config_id")
    op.drop_column("commercial_routing_config", "auto_apply_confidence")
    op.drop_column("commercial_routing_config", "auto_apply_source_event_count")
    op.drop_column("commercial_routing_config", "auto_apply_reason")
    op.drop_column("commercial_routing_config", "can_auto_apply")
    op.drop_column("commercial_routing_config", "auto_applied")
    op.drop_column("commercial_routing_config", "canary_enabled")
    op.drop_column("commercial_routing_config", "canary_percent")
