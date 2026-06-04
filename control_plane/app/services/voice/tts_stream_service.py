# Owner: voice-agent
import logging
from typing import AsyncGenerator, Optional

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

POCKET_TTS_URL = "http://pocket-tts:8000"


class TTSStreamService:
    """
    Text-to-Speech streaming service.

    Providers:
    - mock: yields synthetic audio chunks
    - pocket_tts: proxies to existing Pocket-TTS microservice
    - elevenlabs: placeholder for ElevenLabs streaming API
    """

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        tenant_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text to audio chunks."""
        if self.provider == "mock":
            async for chunk in self._mock_synthesize(text):
                yield chunk
        elif self.provider == "pocket_tts":
            async for chunk in self._pocket_tts_synthesize(text, voice, tenant_id):
                yield chunk
        elif self.provider == "elevenlabs":
            async for chunk in self._elevenlabs_synthesize(text, voice):
                yield chunk
        else:
            logger.warning(f"Unknown TTS provider: {self.provider}")
            yield b""

    async def _mock_synthesize(self, text: str) -> AsyncGenerator[bytes, None]:
        """Mock TTS: yields 3 synthetic audio chunks."""
        logger.debug(f"Mock TTS: synthesizing '{text[:50]}...'")
        for i in range(3):
            yield f"AUDIO_CHUNK_{i}_DATA".encode()

    async def _pocket_tts_synthesize(
        self, text: str, voice: str, tenant_id: Optional[str]
    ) -> AsyncGenerator[bytes, None]:
        """Proxy to Pocket-TTS microservice."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{POCKET_TTS_URL}/tts",
                    data={"text": text, "voice": voice},
                    headers={"X-Client-ID": tenant_id or ""} if tenant_id else {},
                )
                if resp.status_code == 200:
                    yield resp.content
                else:
                    logger.warning(f"Pocket-TTS returned {resp.status_code}")
                    yield b""
        except httpx.RequestError as e:
            logger.error(f"Pocket-TTS unreachable: {e}")
            yield b""

    async def _elevenlabs_synthesize(self, text: str, voice: str) -> AsyncGenerator[bytes, None]:
        """Placeholder for ElevenLabs streaming TTS."""
        logger.debug(f"ElevenLabs TTS placeholder: '{text[:50]}...'")
        yield b""
