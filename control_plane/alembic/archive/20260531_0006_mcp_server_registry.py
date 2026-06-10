"""persist agent mcp server registry

Revision ID: 20260531_0006
Revises: 20260530_0005
Create Date: 2026-05-31 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260531_0006"
down_revision: Union[str, Sequence[str], None] = "20260530_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_mcp_registry import AgentMCPServer

    bind = op.get_bind()
    Base.metadata.create_all(bind, tables=[AgentMCPServer.__table__])


def downgrade() -> None:
    op.drop_table("agent_mcp_servers")
