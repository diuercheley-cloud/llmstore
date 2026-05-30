# Voice Agent - WebSocket & WebRTC Foundation

Real-time voice conversation with agents via STT/TTS streaming.

## Architecture

```
control_plane/app/
  models/realtime_voice.py         # VoiceSession, VoiceTurn, VoiceTranscript, VoiceStreamEvent
  api/voice.py                     # REST + WebSocket endpoints
  services/voice/
    voice_session_service.py       # Session lifecycle management
    stt_stream_service.py          # Speech-to-Text streaming (mock/local/deepgram/whisper)
    tts_stream_service.py          # Text-to-Speech streaming (mock/pocket_tts/elevenlabs)
    turn_detection.py              # VAD + turn boundary detection
    voice_agent_bridge.py          # Bridges voice turns to agent sessions
  services/realtime_voice/         # Legacy services (kept for backward compat)
```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `VOICE_AGENT_ENABLED` | `false` | Gates all `/v1/voice/*` endpoints |
| `VOICE_STT_STREAMING_ENABLED` | `false` | Enables STT streaming providers |
| `VOICE_TTS_STREAMING_ENABLED` | `false` | Enables TTS audio streaming over WebSocket |
| `WEBRTC_VOICE_ENABLED` | `false` | Enables WebRTC SDP offer/answer endpoint |

Set in environment:
```bash
VOICE_AGENT_ENABLED=true
VOICE_TTS_STREAMING_ENABLED=true
```

## API Endpoints

### REST

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/voice/sessions` | Create voice session |
| GET | `/v1/voice/sessions` | List voice sessions |
| GET | `/v1/voice/sessions/{id}` | Get voice session |
| DELETE | `/v1/voice/sessions/{id}` | End voice session |
| POST | `/v1/voice/webrtc/offer` | WebRTC SDP signaling |

### WebSocket

| Path | Description |
|------|-------------|
| `WS /v1/voice/sessions/{id}/stream?token=...` | Real-time voice streaming |

## WebSocket Protocol

### Client -> Server

| Type | Format | Description |
|------|--------|-------------|
| Audio | Binary | Raw audio chunk (PCM/Opus) |
| end_turn | JSON | User finished speaking |
| cancel | JSON | Cancel current processing |

### Server -> Client

| Type | Description |
|------|-------------|
| `session_ready` | Session initialized |
| `transcript` | STT result (user speech) |
| `agent_thinking` | Agent processing started |
| `agent_response` | Agent text response |
| `tts_audio_start` | TTS audio stream beginning |
| Audio (binary) | TTS audio chunk |
| `tts_audio_end` | TTS audio stream ended |
| `turn_complete` | Full turn cycle done |
| `error` | Error occurred |

## Voice Pipeline

```
User speaks
  -> Audio chunks via WebSocket
  -> VAD (is_speech / is_turn_complete)
  -> STT (transcribe audio to text)
  -> VoiceAgentBridge (create agent session message)
  -> Agent processes (or mock response)
  -> TTS (synthesize response to audio)
  -> Audio chunks back to client
  -> Transcript persisted (no raw audio)
```

## Models

### VoiceSession
- `id`, `tenant_id`, `agent_id`, `agent_session_id`
- `status`: starting | active | ended
- `mode`: websocket | webrtc
- `stt_provider`, `tts_provider`, `language`

### VoiceTurn
- `id`, `session_id`, `turn_number`
- `user_text`, `agent_text`, `agent_run_id`
- `status`: listening | processing | speaking | completed | error
- `raw_audio_ref`: storage path (NOT raw bytes)
- `duration_ms`, `audio_sample_rate`, `audio_format`

### VoiceTranscript
- `id`, `session_id`, `turn_id`
- `speaker`: user | agent
- `text`, `confidence`

## Security

- Bearer auth on REST endpoints
- Token-based WebSocket auth
- Tenant isolation on all queries
- Raw audio NOT persisted by default (`raw_audio_ref` is a path, not data)
- Feature flags disabled by default

## Testing

- Create session: `POST /v1/voice/sessions` with agent_id
- Audio mock: send 42-byte chunk -> get transcript
- Transcript creates message in agent session
- TTS mock yields 3 audio chunks
- Raw audio never stored in database

## Integration with Existing Voice Infrastructure

This module coexists with `services/realtime_voice/`:
- `realtime_voice/` provides the original session/audio services
- `voice/` provides the enhanced agent-bridge services
- Both share the same database models in `models/realtime_voice.py`
- The new `voice.py` API replaces the old one (same router path)
