import logging
import uuid
from typing import Optional

from app.models.core.realtime_voice import VoiceStreamEvent, VoiceTranscript
from sqlalchemy.ext.asyncio import AsyncSession

from .stt_stream import STTStreamService
from .tts_stream import TTSStreamService
from .voice_turn_detection import VoiceTurnDetectionService

logger = logging.getLogger(__name__)

class AudioStreamService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stt = STTStreamService()
        self.tts = TTSStreamService()
        self.vad = VoiceTurnDetectionService()

    async def process_audio_chunk(self, session_id: uuid.UUID, audio_data: bytes) -> Optional[str]:
        # 1. Voice Activity Detection
        if not await self.vad.is_speech(audio_data):
            return None

        # 2. STT (Speech to Text)
        transcript = await self.stt.transcribe_chunk(audio_data)
        if transcript:
            # 3. Store transcript if it's a complete turn
            if await self.vad.is_turn_complete(audio_data):
                voice_transcript = VoiceTranscript(
                    session_id=session_id,
                    speaker="user",
                    text=transcript
                )
                self.db.add(voice_transcript)
                await self.db.flush()
                return transcript
        return None

    async def generate_response_audio(self, session_id: uuid.UUID, text: str):
        # 1. TTS (Text to Speech)
        audio_stream = self.tts.synthesize_stream(text)
        
        # 2. Log TTS start event
        event = VoiceStreamEvent(
            session_id=session_id,
            event_type="tts_start",
            payload={"text_length": len(text)}
        )
        self.db.add(event)
        
        # 3. Log transcript for agent
        voice_transcript = VoiceTranscript(
            session_id=session_id,
            speaker="agent",
            text=text
        )
        self.db.add(voice_transcript)
        await self.db.flush()
        
        return audio_stream
