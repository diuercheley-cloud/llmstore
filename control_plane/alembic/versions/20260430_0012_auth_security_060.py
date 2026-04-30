"""Add scopes to ApiKey and JWT settings for Release 0.6.0-local"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_0012"
down_revision = "20260430_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scopes to api_keys
    op.add_column("api_keys", sa.Column("scopes_json", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "scopes_json")
