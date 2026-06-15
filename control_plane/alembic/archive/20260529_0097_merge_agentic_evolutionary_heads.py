"""merge agentic evolutionary heads

Revision ID: 20260529_0097
Revises: 20260529_0096, 7d0ea3d718fb
Create Date: 2026-05-29 17:45:00.000000

"""

from collections.abc import Sequence
from typing import Union

revision: str = "20260529_0097"
down_revision: Union[str, Sequence[str], None] = ("20260529_0096", "7d0ea3d718fb")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
