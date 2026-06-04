"""inference backends and model backend binding"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260430_0006"
down_revision = "20260430_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inference_backends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("backend_url", sa.String(length=255), nullable=False),
        sa.Column("healthcheck_path", sa.String(length=64), nullable=False, server_default="/health"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="configured"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inference_backends_name", "inference_backends", ["name"])
    op.add_column("model_registry", sa.Column("inference_backend_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_model_registry_inference_backend_id", "model_registry", ["inference_backend_id"])
    op.create_foreign_key(
        "fk_model_registry_inference_backend_id",
        "model_registry",
        "inference_backends",
        ["inference_backend_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_model_registry_inference_backend_id", "model_registry", type_="foreignkey")
    op.drop_index("ix_model_registry_inference_backend_id", table_name="model_registry")
    op.drop_column("model_registry", "inference_backend_id")
    op.drop_index("ix_inference_backends_name", table_name="inference_backends")
    op.drop_table("inference_backends")
