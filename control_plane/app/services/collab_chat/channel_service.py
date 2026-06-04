import uuid
from typing import List, Optional

from app.models.collab_chat import ChatChannel, ChatChannelMember
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_channel(
        self, tenant_id: str, name: str, description: Optional[str] = None, is_private: bool = False
    ) -> ChatChannel:
        channel = ChatChannel(
            tenant_id=tenant_id,
            name=name,
            description=description,
            is_private=is_private
        )
        self.db.add(channel)
        await self.db.flush()
        return channel

    async def get_channels(self, tenant_id: str) -> List[ChatChannel]:
        stmt = select(ChatChannel).where(ChatChannel.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[ChatChannel]:
        return await self.db.get(ChatChannel, channel_id)

    async def add_member(self, channel_id: uuid.UUID, user_id: str, role: str = "member") -> ChatChannelMember:
        member = ChatChannelMember(
            channel_id=channel_id,
            user_id=user_id,
            role=role
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def is_member(self, channel_id: uuid.UUID, user_id: str) -> bool:
        stmt = select(ChatChannelMember).where(
            ChatChannelMember.channel_id == channel_id,
            ChatChannelMember.user_id == user_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None
