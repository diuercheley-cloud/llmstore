# Owner: voice-agent
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TurnDetectionService:
    """
    Voice Activity Detection (VAD) and turn boundary detection.

    Detects:
    - Speech start/end (is_speech)
    - Turn completion (is_turn_complete) via silence threshold

    This is a foundation/mock. Real implementations would use:
    - WebRTC VAD
    - Silero VAD model
    - Energy-based detection
    """

    def __init__(self, silence_threshold_ms: int = 800, min_speech_ms: int = 200):
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_ms = min_speech_ms
        self._speech_buffer_size = 0
        self._silence_counter = 0

    async def is_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech."""
        if not audio_chunk:
            return False
        # Mock: any non-trivial audio chunk is considered speech
        if len(audio_chunk) > 10:
            self._speech_buffer_size += len(audio_chunk)
            self._silence_counter = 0
            return True
        # Small chunk = potential silence
        self._silence_counter += 1
        return False

    async def is_turn_complete(self, audio_chunk: bytes) -> bool:
        """Detect if user has finished speaking (turn boundary)."""
        if not audio_chunk:
            # Empty chunk with prior speech = turn end
            if self._speech_buffer_size > 0:
                self._speech_buffer_size = 0
                self._silence_counter = 0
                return True
            return False

        # If we accumulate enough silence after speech, it's a turn end
        if len(audio_chunk) <= 10 and self._speech_buffer_size > 0:
            self._silence_counter += 1
            # After ~5 silence chunks, consider turn complete
            if self._silence_counter >= 5:
                self._speech_buffer_size = 0
                self._silence_counter = 0
                return True
        else:
            self._silence_counter = 0

        return False

    def reset(self):
        self._speech_buffer_size = 0
        self._silence_counter = 0
