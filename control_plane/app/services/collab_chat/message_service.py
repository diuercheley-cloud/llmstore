import re
import uuid
from typing import Any

from app.models.agents.collab_chat import ChatMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        channel_id: uuid.UUID,
        user_id: str | None = None,
        agent_id: uuid.UUID | None = None,
        content: str = "",
        message_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            channel_id=channel_id,
            user_id=user_id,
            agent_id=agent_id,
            content=content,
            message_type=message_type,
            metadata_json=metadata,
        )
        self.db.add(message)
        await self.db.flush()

        # Check for agent mentions if it's a user message
        if user_id and message_type == "text":
            await self._handle_mentions(message)

        return message

    async def get_messages(self, channel_id: uuid.UUID, limit: int = 50) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.channel_id == channel_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(reversed(res.scalars().all()))

    async def _handle_mentions(self, message: ChatMessage):
        # Basic mention pattern: @agent_name or @[uuid]
        mentions = re.findall(r"@\[([a-f0-9\-]{36})\]", message.content)
        if mentions:
            from .agent_participant import AgentParticipantService

            agent_svc = AgentParticipantService(self.db)
            for agent_id_str in mentions:
                try:
                    agent_id = uuid.UUID(agent_id_str)
                    await agent_svc.trigger_agent_run(
                        message.channel_id, agent_id, message.user_id, message.content
                    )
                except ValueError:
                    continue
