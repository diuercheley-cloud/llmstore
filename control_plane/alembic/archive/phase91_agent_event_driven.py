"""agent event driven tables and merge heads

Revision ID: phase91_agent_event_driven
Revises: ('20260522_0095', '20260523_0092')
Create Date: 2026-05-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'phase91_agent_event_driven'
down_revision: Union[str, Sequence[str], None] = ('20260522_0095', '20260523_0092')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_events import (
        AgentEventDedupKey,
        AgentEventDelivery,
        AgentEventSource,
        AgentEventSubscription,
        AgentEventTrigger,
        AgentScheduledTrigger,
        AgentWebhookTrigger,
    )
    bind = op.get_bind()
    tables = [
        AgentEventSource.__table__,
        AgentEventTrigger.__table__,
        AgentEventDelivery.__table__,
        AgentEventDedupKey.__table__,
        AgentEventSubscription.__table__,
        AgentScheduledTrigger.__table__,
        AgentWebhookTrigger.__table__
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_webhook_triggers')
    op.drop_table('agent_scheduled_triggers')
    op.drop_table('agent_event_subscriptions')
    op.drop_table('agent_event_dedup_keys')
    op.drop_table('agent_event_deliveries')
    op.drop_table('agent_event_triggers')
    op.drop_table('agent_event_sources')
