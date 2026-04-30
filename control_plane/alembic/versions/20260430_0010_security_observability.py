"""security events, ip policy, and correlation observability"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_0010"
down_revision = "20260430_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("ip_allowlist_json", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("ip_blocklist_json", sa.Text(), nullable=True))
    op.add_column("request_logs", sa.Column("correlation_id", sa.String(length=64), nullable=True))
    op.add_column("request_logs", sa.Column("source_ip", sa.String(length=64), nullable=True))
    op.create_index("ix_request_logs_correlation_id", "request_logs", ["correlation_id"])

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("api_key_prefix", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["request_log_id"], ["request_logs.id"]),
    )
    op.create_index("ix_security_events_client_id", "security_events", ["client_id"])
    op.create_index("ix_security_events_request_log_id", "security_events", ["request_log_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_correlation_id", "security_events", ["correlation_id"])
    op.create_index("ix_security_events_source_ip", "security_events", ["source_ip"])
    op.create_index("ix_security_events_api_key_prefix", "security_events", ["api_key_prefix"])


def downgrade() -> None:
    op.drop_index("ix_security_events_api_key_prefix", table_name="security_events")
    op.drop_index("ix_security_events_source_ip", table_name="security_events")
    op.drop_index("ix_security_events_correlation_id", table_name="security_events")
    op.drop_index("ix_security_events_severity", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_request_log_id", table_name="security_events")
    op.drop_index("ix_security_events_client_id", table_name="security_events")
    op.drop_table("security_events")
    op.drop_index("ix_request_logs_correlation_id", table_name="request_logs")
    op.drop_column("request_logs", "source_ip")
    op.drop_column("request_logs", "correlation_id")
    op.drop_column("clients", "ip_blocklist_json")
    op.drop_column("clients", "ip_allowlist_json")
