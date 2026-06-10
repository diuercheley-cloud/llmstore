"""create shared artifact registry tables

Revision ID: 20260527_0094
Revises: phase93_agent_optimization
Create Date: 2026-05-27 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260527_0094'
down_revision: Union[str, Sequence[str], None] = 'phase93_agent_optimization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_workspace import (
        AgentArtifactComment,
        AgentArtifactEvent,
        AgentArtifactLock,
        AgentArtifactReview,
        AgentArtifactVersion,
        AgentSharedArtifact,
        AgentWorkspace,
    )
    bind = op.get_bind()
    tables = [
        AgentWorkspace.__table__,
        AgentSharedArtifact.__table__,
        AgentArtifactVersion.__table__,
        AgentArtifactLock.__table__,
        AgentArtifactReview.__table__,
        AgentArtifactComment.__table__,
        AgentArtifactEvent.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_artifact_events')
    op.drop_table('agent_artifact_comments')
    op.drop_table('agent_artifact_reviews')
    op.drop_table('agent_artifact_locks')
    op.drop_table('agent_artifact_versions')
    op.drop_table('agent_shared_artifacts')
    op.drop_table('agent_workspaces')
