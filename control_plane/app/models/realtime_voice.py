import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="starting")  # starting|active|ended
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events = relationship("VoiceStreamEvent", back_populates="session", cascade="all, delete-orphan")
    transcripts = relationship("VoiceTranscript", back_populates="session", cascade="all, delete-orphan")

class VoiceStreamEvent(Base):
    __tablename__ = "voice_stream_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False) # audio_chunk|stt_result|tts_start|voice_activity
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session = relationship("VoiceSession", back_populates="events")

class VoiceTranscript(Base):
    __tablename__ = "voice_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker: Mapped[str] = mapped_column(String(32), nullable=False) # user|agent
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session = relationship("VoiceSession", back_populates="transcripts")
