# Voice Agent System

## Overview

The Voice Agent system enables real-time audio interaction with agents using WebSocket and WebRTC. It provides a stateful bridge between voice streams and the existing agent session system, allowing users to talk to agents and receive spoken responses.

## Key Components

### Voice Sessions
- **Lifecycle**: Managed via `VoiceSessionService`. Sessions can be created, activated, and ended.
- **Persistence**: Stored in the `voice_sessions` table.

### Streaming Services
- **STT (Speech-to-Text)**: `STTStreamService` handles incoming audio chunks and converts them to text using providers like Whisper (local or API).
- **TTS (Text-to-Speech)**: `TTSStreamService` converts agent response text back into audio chunks for the client.
- **Turn Detection**: `TurnDetectionService` uses Voice Activity Detection (VAD) to identify when a user starts and stops speaking.

### Voice-Agent Bridge
- **`VoiceAgentBridge`**: The orchestrator that:
  - Links voice turns to agent session messages.
  - Creates or attaches to a persistent `AgentSession`.
  - Records transcripts for audit and debugging.

## API & WebSocket Protocol

### Create Voice Session
```
POST /v1/voice/sessions
```
Initializes a voice session for a specific agent.

### WebSocket Stream
```
WS /v1/voice/sessions/{session_id}/stream?token={client_token}
```
The primary bidirectional channel for voice interaction.

#### Client-to-Server
- **Binary**: Raw audio data (PCM/Opus).
- **JSON Control**:
  - `{"type": "end_turn"}`: Manually signal the end of a speaking turn.
  - `{"type": "cancel"}`: Abort the current processing turn.

#### Server-to-Client
- `{"type": "transcript", "text": "...", "speaker": "user"}`
- `{"type": "agent_thinking"}`
- `{"type": "agent_response", "text": "..."}`
- `{"type": "tts_audio_start"}`
- **Binary**: Audio chunks from TTS.
- `{"type": "tts_audio_end"}`

## Feature Flags

The system is modular and controlled via the following flags:
- `VOICE_AGENT_ENABLED`: Master switch for voice features.
- `VOICE_STT_STREAMING_ENABLED`: Enables real-time transcription.
- `VOICE_TTS_STREAMING_ENABLED`: Enables real-time speech synthesis.
- `WEBRTC_VOICE_ENABLED`: Enables WebRTC signaling endpoints.

## Security & Privacy
- **Raw Audio**: Raw audio bytes are **not** persisted to the database by default to ensure privacy and efficiency. Only transcripts and metadata are stored.
- **Tenant Isolation**: Strict isolation ensures that voice sessions and transcripts are only accessible within the authorized tenant scope.
