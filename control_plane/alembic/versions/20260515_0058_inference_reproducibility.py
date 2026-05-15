"""Phase 40 deterministic inference reproducibility controls

Revision ID: 20260515_0058
Revises: 20260515_0057
Create Date: 2026-05-15 03:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0058"
down_revision = "20260515_0057"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_inference_reproducibility_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_alias", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("backend_name", sa.String(length=255), nullable=True),
        sa.Column("tokenizer_name", sa.String(length=255), nullable=True),
        sa.Column("tokenizer_version", sa.String(length=128), nullable=True),
        sa.Column("chat_template_hash", sa.String(length=128), nullable=True),
        sa.Column("prompt_hash", sa.String(length=128), nullable=False),
        sa.Column("request_payload_hash", sa.String(length=128), nullable=False),
        sa.Column("response_payload_hash", sa.String(length=128), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("min_p", sa.Float(), nullable=True),
        sa.Column("repetition_penalty", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("runtime_engine", sa.String(length=128), nullable=True),
        sa.Column("runtime_engine_version", sa.String(length=128), nullable=True),
        sa.Column("model_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("model_checksum", sa.String(length=128), nullable=True),
        sa.Column("runtime_config_hash", sa.String(length=128), nullable=True),
        sa.Column("replay_supported", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("replay_status", sa.String(length=32), nullable=False, server_default="original"),
        sa.Column("replay_similarity", sa.Float(), nullable=True),
        sa.Column("replay_distance", sa.Float(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "request_id",
        "correlation_id",
        "client_id",
        "model_name",
        "model_alias",
        "provider",
        "backend_name",
        "chat_template_hash",
        "prompt_hash",
        "request_payload_hash",
        "response_payload_hash",
        "model_manifest_hash",
        "model_checksum",
        "runtime_config_hash",
        "replay_status",
        "immutable_hash",
    ):
        op.create_index(
            op.f(f"ix_commercial_inference_reproducibility_records_{column}"),
            "commercial_inference_reproducibility_records",
            [column],
            unique=False,
        )

    op.create_table(
        "commercial_inference_replay_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("reproducibility_record_id", _uuid_type(), nullable=False),
        sa.Column("replay_type", sa.String(length=32), nullable=False),
        sa.Column("replay_result", sa.String(length=32), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("distance_score", sa.Float(), nullable=True),
        sa.Column("replay_output_hash", sa.String(length=128), nullable=True),
        sa.Column("replay_runtime_hash", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reproducibility_record_id"],
            ["commercial_inference_reproducibility_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("reproducibility_record_id", "replay_type", "replay_result"):
        op.create_index(
            op.f(f"ix_commercial_inference_replay_events_{column}"),
            "commercial_inference_replay_events",
            [column],
            unique=False,
        )

    op.create_table(
        "commercial_inference_runtime_snapshots",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("backend_name", sa.String(length=255), nullable=False),
        sa.Column("runtime_engine", sa.String(length=128), nullable=False),
        sa.Column("runtime_engine_version", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("runtime_config_json", sa.JSON(), nullable=True),
        sa.Column("tokenizer_info_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("backend_name", "runtime_engine", "model_name", "model_manifest_hash", "snapshot_hash"):
        op.create_index(
            op.f(f"ix_commercial_inference_runtime_snapshots_{column}"),
            "commercial_inference_runtime_snapshots",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("snapshot_hash", "model_manifest_hash", "model_name", "runtime_engine", "backend_name"):
        op.drop_index(op.f(f"ix_commercial_inference_runtime_snapshots_{column}"), table_name="commercial_inference_runtime_snapshots")
    op.drop_table("commercial_inference_runtime_snapshots")

    for column in ("replay_result", "replay_type", "reproducibility_record_id"):
        op.drop_index(op.f(f"ix_commercial_inference_replay_events_{column}"), table_name="commercial_inference_replay_events")
    op.drop_table("commercial_inference_replay_events")

    for column in (
        "immutable_hash",
        "replay_status",
        "runtime_config_hash",
        "model_checksum",
        "model_manifest_hash",
        "response_payload_hash",
        "request_payload_hash",
        "prompt_hash",
        "chat_template_hash",
        "backend_name",
        "provider",
        "model_alias",
        "model_name",
        "client_id",
        "correlation_id",
        "request_id",
    ):
        op.drop_index(
            op.f(f"ix_commercial_inference_reproducibility_records_{column}"),
            table_name="commercial_inference_reproducibility_records",
        )
    op.drop_table("commercial_inference_reproducibility_records")
