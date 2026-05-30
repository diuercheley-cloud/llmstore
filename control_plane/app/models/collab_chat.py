import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class ChatChannel(Base):
    __tablename__ = "chat_channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    members = relationship("ChatChannelMember", back_populates="channel", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="channel", cascade="all, delete-orphan")
    agent_participants = relationship("ChatAgentParticipant", back_populates="channel", cascade="all, delete-orphan")

class ChatChannelMember(Base):
    __tablename__ = "chat_channel_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="member")  # member|admin
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    channel = relationship("ChatChannel", back_populates="members")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), default="text")  # text|system|agent_response
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    channel = relationship("ChatChannel", back_populates="messages")

class ChatAgentParticipant(Base):
    __tablename__ = "chat_agent_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    auto_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    channel = relationship("ChatChannel", back_populates="agent_participants")

class ChatPresenceEvent(Base):
    __tablename__ = "chat_presence_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # online|offline|away
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
