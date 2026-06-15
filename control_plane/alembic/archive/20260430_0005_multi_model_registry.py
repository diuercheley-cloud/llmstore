"""multi-model registry and model access policies"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0005"
down_revision = "20260430_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_registry", sa.Column("model_alias", sa.String(length=128), nullable=True))
    op.add_column(
        "model_registry",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_model_registry_model_alias", "model_registry", ["model_alias"], unique=True)

    op.add_column("billing_plans", sa.Column("allowed_models_json", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("allowed_models_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "allowed_models_json")
    op.drop_column("billing_plans", "allowed_models_json")
    op.drop_index("ix_model_registry_model_alias", table_name="model_registry")
    op.drop_column("model_registry", "is_default")
    op.drop_column("model_registry", "model_alias")
