"""Add system prompt, prompt template and safety profile for Release 0.5.0-local"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0011"
down_revision = "20260430_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add system_prompt to clients
    op.add_column("clients", sa.Column("system_prompt", sa.Text(), nullable=True))

    # Add prompt_template to model_registry
    op.add_column("model_registry", sa.Column("prompt_template", sa.Text(), nullable=True))

    # Add safety_profile to ChatCompletionRequest and CompletionRequest is handled at schema level,
    # but we might want to store it in request_logs for auditing.
    op.add_column(
        "request_logs",
        sa.Column("safety_profile", sa.String(length=32), nullable=True, server_default="default"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "safety_profile")
    op.drop_column("model_registry", "prompt_template")
    op.drop_column("clients", "system_prompt")
