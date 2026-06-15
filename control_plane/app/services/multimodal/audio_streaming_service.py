import logging
import uuid
from collections.abc import AsyncGenerator

from app.services.multimodal.multimodal_policy import MultimodalPolicyService
from app.services.multimodal.multimodal_usage import MultimodalUsageService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AudioStreamingService:
    def __init__(self):
        self.policy_service = MultimodalPolicyService()
        self.usage_service = MultimodalUsageService()

    async def initialize_session(self, db: AsyncSession, client_id: uuid.UUID) -> str:
        # 1. Policy check for real-time audio streaming
        await self.policy_service.check_policy(db, client_id, "audio-streaming")

        session_id = str(uuid.uuid4())
        logger.info(
            f"Initialized real-time audio streaming session: {session_id} for client: {client_id}"
        )
        return session_id

    async def stream_audio_response(
        self, db: AsyncSession, client_id: uuid.UUID, session_id: str, input_prompt: str
    ) -> AsyncGenerator[bytes, None]:
        """
        Mock real-time audio streaming output (chunk generator).
        """
        # Log usage (say, 5 seconds of stream)
        req = await self.usage_service.log_request(
            db,
            client_id,
            "audio-streaming",
            "completed",
            metadata_json={"session_id": session_id, "prompt": input_prompt},
        )
        await self.usage_service.record_usage(
            db, client_id, req.id, "audio-streaming", unit_count=5
        )

        # Yield 5 mock chunks of audio data
        for i in range(5):
            # Mock audio wave bytes chunk
            yield b"MOCK_AUDIO_STREAM_CHUNK_" + str(i).encode()
