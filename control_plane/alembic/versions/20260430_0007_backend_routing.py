"""backend routing and request log routing telemetry"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260430_0007"
down_revision = "20260430_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_backend_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inference_backend_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inference_backends.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="healthy"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("model_registry_id", "inference_backend_id", name="uq_model_backend_route"),
    )
    op.create_index("ix_model_backend_routes_model_registry_id", "model_backend_routes", ["model_registry_id"])
    op.create_index("ix_model_backend_routes_inference_backend_id", "model_backend_routes", ["inference_backend_id"])
    op.create_index("ix_model_backend_routes_state", "model_backend_routes", ["state"])

    op.add_column("request_logs", sa.Column("backend_name", sa.String(length=120), nullable=True))
    op.add_column("request_logs", sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("request_logs", sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("request_logs", sa.Column("backend_errors_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_logs", "backend_errors_json")
    op.drop_column("request_logs", "fallback_used")
    op.drop_column("request_logs", "attempts")
    op.drop_column("request_logs", "backend_name")
    op.drop_index("ix_model_backend_routes_state", table_name="model_backend_routes")
    op.drop_index("ix_model_backend_routes_inference_backend_id", table_name="model_backend_routes")
    op.drop_index("ix_model_backend_routes_model_registry_id", table_name="model_backend_routes")
    op.drop_table("model_backend_routes")
