"""generation jobs queue and backend concurrency controls"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_0009"
down_revision = "20260430_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inference_backends",
        sa.Column("max_parallel_requests", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "inference_backends",
        sa.Column("current_running", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inference_backend_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("endpoint", sa.String(length=64), nullable=False, server_default="/v1/chat/completions/async"),
        sa.Column("requested_model", sa.String(length=255), nullable=False),
        sa.Column("resolved_model", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("is_stream", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("include_reasoning", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("backend_name", sa.String(length=120), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("backend_errors_json", sa.Text(), nullable=True),
        sa.Column("prompt_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("max_tokens_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["model_registry_id"], ["model_registry.id"]),
        sa.ForeignKeyConstraint(["inference_backend_id"], ["inference_backends.id"]),
    )
    op.create_index("ix_generation_jobs_client_id", "generation_jobs", ["client_id"])
    op.create_index("ix_generation_jobs_model_registry_id", "generation_jobs", ["model_registry_id"])
    op.create_index("ix_generation_jobs_inference_backend_id", "generation_jobs", ["inference_backend_id"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_status", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_inference_backend_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_model_registry_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_client_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
    op.drop_column("inference_backends", "current_running")
    op.drop_column("inference_backends", "max_parallel_requests")
