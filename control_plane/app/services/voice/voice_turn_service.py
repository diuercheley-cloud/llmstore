# Owner: voice-agent
import asyncio
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.agent_sessions import AgentThreadMessage
from app.models.agents.agents import AgentMemoryItem
from app.models.core.realtime_voice import VoiceSession, VoiceStreamEvent
from app.services.agents import agent_runtime
from app.services.voice.voice_agent_bridge import VoiceAgentBridge
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VoiceTurnService:
    """
    Orchestrates a voice turn: transcription -> agent runtime -> response.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bridge = VoiceAgentBridge(db)

    async def process_turn(
        self,
        voice_session: VoiceSession,
        turn_number: int,
        transcript_text: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrates the full voice turn flow.
        """
        # 1. Audit: voice_turn_started
        await self._emit_audit_event(
            voice_session.id,
            "voice_turn_started",
            {"turn_number": turn_number, "correlation_id": correlation_id},
        )

        # 2. Process user turn via bridge (persistence and thread update)
        turn = await self.bridge.process_user_turn(voice_session, turn_number, transcript_text)
        await self.db.flush()

        agent_text = None
        agent_run_id = None
        fallback_used = False

        try:
            # 3. Call agent_runtime
            # We assume synchronous execution for voice turns to get the response immediately
            run = await agent_runtime.start_run(
                self.db,
                agent_id=voice_session.agent_id,
                tenant_id=voice_session.tenant_id,
                input_text=transcript_text,
                session_id=voice_session.agent_session_id,
                correlation_id=correlation_id,
            )
            agent_run_id = run.id

            # Wait for completion if not already finished (usually it is if sync)
            timeout = 30
            start_time = utc_now()
            while run.status not in ("completed", "failed", "cancelled"):
                await asyncio.sleep(0.5)
                await self.db.refresh(run)
                if (utc_now() - start_time).total_seconds() > timeout:
                    logger.warning(
                        f"Agent run {run.id} timed out for voice session {voice_session.id}"
                    )
                    break

            if run.status == "completed":
                # 4. Extract agent response text
                # Primary source: Short-term memory (written by AgentExecutor)
                agent_text = await self._get_text_from_memory(run.id)

                # Secondary source: Conversation thread (just in case)
                if not agent_text:
                    agent_text = await self._get_text_from_thread(run.id)

                if not agent_text:
                    logger.error(f"Agent run {run.id} completed but no output text found")
                    raise RuntimeError("No response text found from agent")

                # 5. Complete turn via bridge
                await self.bridge.complete_agent_turn(turn, agent_text, agent_run_id=run.id)

                # 6. Audit: voice_turn_completed
                await self._emit_audit_event(
                    voice_session.id,
                    "voice_turn_completed",
                    {
                        "turn_number": turn_number,
                        "run_id": str(run.id),
                        "agent_text_length": len(agent_text),
                    },
                )
            else:
                error_msg = run.failure_reason or f"Agent run failed with status: {run.status}"
                logger.error(
                    f"Agent run {run.id} failed for voice session {voice_session.id}: {error_msg}"
                )
                raise RuntimeError(error_msg)

        except Exception as e:
            logger.exception(f"Error during voice turn processing for session {voice_session.id}")
            # 7. Fallback Mechanism
            fallback_text = "Desculpe, tive um problema técnico ao processar sua solicitação."
            agent_text = fallback_text
            fallback_used = True

            await self.bridge.error_turn(turn, str(e))
            # Even on error, we might want to provide the fallback text to the user
            # We don't call complete_agent_turn because it sets status to 'completed'
            # Instead we manually add the fallback transcript if needed, or just return it.

            # 8. Audit: voice_turn_failed / voice_turn_fallback_used
            await self._emit_audit_event(voice_session.id, "voice_turn_failed", {"error": str(e)})
            await self._emit_audit_event(
                voice_session.id,
                "voice_turn_fallback_used",
                {"fallback_text": fallback_text, "reason": str(e)},
            )

        await self.db.commit()

        return {
            "text": agent_text,
            "turn_number": turn_number,
            "agent_run_id": str(agent_run_id) if agent_run_id else None,
            "correlation_id": correlation_id,
            "fallback": fallback_used,
        }

    async def _get_text_from_memory(self, run_id: uuid.UUID) -> str | None:
        stmt = (
            select(AgentMemoryItem)
            .where(
                AgentMemoryItem.source_run_id == run_id, AgentMemoryItem.memory_type == "short_term"
            )
            .order_by(AgentMemoryItem.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        return item.raw_content if item else None

    async def _get_text_from_thread(self, run_id: uuid.UUID) -> str | None:
        stmt = (
            select(AgentThreadMessage)
            .where(AgentThreadMessage.run_id == run_id, AgentThreadMessage.role == "assistant")
            .order_by(AgentThreadMessage.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        msg = res.scalar_one_or_none()
        return msg.content if msg else None

    async def _emit_audit_event(self, session_id: uuid.UUID, event_type: str, payload: dict):
        event = VoiceStreamEvent(session_id=session_id, event_type=event_type, payload=payload)
        self.db.add(event)
        await self.db.flush()
