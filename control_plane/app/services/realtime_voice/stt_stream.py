import logging

logger = logging.getLogger(__name__)


class STTStreamService:
    """
    Mock/Foundation for Real-time STT.
    """

    async def transcribe_chunk(self, audio_data: bytes) -> str | None:
        # In a real implementation, this would call a streaming STT provider (e.g. Whisper, Google, AWS)
        # For foundation/mock, we just log and return nothing unless it's a test case
        logger.debug(f"Transcribing audio chunk of size {len(audio_data)}")

        # Mock logic: if audio_data is exactly 42 bytes, return a fixed transcript for testing
        if len(audio_data) == 42:
            return "Olá, como posso ajudar?"

        return None
