# Owner: voice-agent
import logging

logger = logging.getLogger(__name__)


class STTStreamService:
    """
    Speech-to-Text streaming service.

    Providers:
    - mock: returns fixed transcript for testing (42-byte trigger)
    - local: placeholder for local whisper.cpp integration
    - deepgram: placeholder for Deepgram streaming API
    - whisper: placeholder for OpenAI Whisper API
    """

    def __init__(self, provider: str = "mock", language: str = "pt-BR"):
        self.provider = provider
        self.language = language
        self._buffer = bytearray()

    async def feed_audio(self, audio_chunk: bytes) -> str | None:
        """Feed raw audio chunk. Returns transcript text if speech detected."""
        self._buffer.extend(audio_chunk)

        if self.provider == "mock":
            return await self._mock_transcribe(audio_chunk)
        elif self.provider == "local":
            return await self._local_transcribe(audio_chunk)
        elif self.provider == "deepgram":
            return await self._deepgram_transcribe(audio_chunk)
        elif self.provider == "whisper":
            return await self._whisper_transcribe(audio_chunk)
        return None

    async def flush(self) -> str | None:
        """Flush buffered audio and return final transcript if available."""
        if not self._buffer:
            return None
        data = bytes(self._buffer)
        self._buffer.clear()
        if self.provider == "mock" and len(data) >= 42:
            return "Audio processado com sucesso."
        return None

    def reset(self):
        self._buffer.clear()

    async def _mock_transcribe(self, audio_chunk: bytes) -> str | None:
        """Mock STT: returns fixed text for 42-byte chunks, None otherwise."""
        if len(audio_chunk) == 42:
            return "Ola, como posso ajudar?"
        if len(audio_chunk) > 100:
            return "Mensagem de audio recebida e processada."
        return None

    async def _local_transcribe(self, audio_chunk: bytes) -> str | None:
        """Placeholder for local whisper.cpp."""
        logger.debug(f"Local STT: chunk size {len(audio_chunk)}")
        return None

    async def _deepgram_transcribe(self, audio_chunk: bytes) -> str | None:
        """Placeholder for Deepgram streaming STT."""
        logger.debug(f"Deepgram STT: chunk size {len(audio_chunk)}")
        return None

    async def _whisper_transcribe(self, audio_chunk: bytes) -> str | None:
        """Placeholder for OpenAI Whisper API."""
        logger.debug(f"Whisper STT: chunk size {len(audio_chunk)}")
        return None
