# Agent Chat - User-Facing Chat UI

User-facing AI assistant interface for chatting with configured agents.

## Architecture

```
frontend/client/src/
  lib/
    types.ts                    # TypeScript types for agents, sessions, messages
    api.ts                      # API client with Bearer token auth
  pages/
    AgentChat.tsx               # Main chat page (orchestrator)
  components/chat/
    AgentSelector.tsx           # Agent dropdown picker
    SessionList.tsx             # Conversation sidebar
    MessageList.tsx             # Message rendering with streaming
    Composer.tsx                # Input with file upload support
    StreamingMessage.tsx        # Real-time streaming display
    ToolActivityTimeline.tsx    # Tool calls, memory reads, approvals
```

## Features

- **Agent selection** - Pick from available agents (filtered to active only)
- **Session management** - Create/resume/delete conversations
- **Persistent history** - Messages loaded from backend on session select
- **WebSocket streaming** - Real-time token-by-token agent responses
- **Tool activity** - Visual timeline of tool calls, memory reads, approvals
- **Cancel runs** - Stop agent execution mid-stream
- **File upload** - Attach up to 5 files (images, PDFs, text)
- **Auth token** - Enter API key via UI, stored in localStorage
- **Responsive** - Mobile sidebar with backdrop overlay
- **Error handling** - Auth prompts, error banners, empty states
- **WebSocket reconnect** - Auto-retry up to 3 times on disconnect
- **Tenant isolation** - Backend validates tenant on all requests

## Authentication

Client API token (Bearer token) is required. Set via:

1. **UI input** - First visit shows a token input prompt
2. **Environment** - Set `VITE_API_TOKEN` in `.env`
3. **localStorage** - Token persisted after first entry

For WebSocket, the token is passed as `?token=` query parameter.

## API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/agents` | List available agents |
| GET | `/v1/agents/{id}` | Get agent details |
| POST | `/v1/agents/sessions/{agent_id}` | Create new session |
| GET | `/v1/agents/sessions?agent_id=...` | List sessions |
| GET | `/v1/agents/sessions/{id}` | Get session |
| GET | `/v1/agents/sessions/{id}/messages` | Get message history |
| POST | `/v1/agents/sessions/{id}/runs` | Start a run in session |
| DELETE | `/v1/agents/sessions/{id}` | Delete session |
| WS | `/v1/agents/runs/{run_id}/stream` | WebSocket streaming |

## WebSocket Event Types

| Event | Description |
|-------|-------------|
| `text_delta` / `content_delta` | Streaming text chunk |
| `step_completed` / `agent_step` | Agent step finished |
| `tool_call` / `tool_invocation` | Tool invocation |
| `memory_read` / `memory_access` | Memory access |
| `approval_required` / `waiting_approval` | Human approval needed |
| `run_completed` / `completed` | Run finished successfully |
| `run_failed` / `failed` | Run failed |
| `run_cancelled` | Run was cancelled |

## Development

```bash
cd frontend/client
npm run dev
```

Set the API target if backend is on a different port:

```bash
VITE_API_TARGET=http://localhost:8080 npm run dev
```

The Vite dev server proxies `/v1/agents` to the control plane.

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_TOKEN` | (none) | Pre-configured API token |
| `VITE_API_BASE_URL` | (empty) | API base URL (for production) |
| `VITE_API_TARGET` | `http://localhost:8080` | Proxy target in dev |

## PWA Considerations

The UI is responsive and works well in mobile browsers. For full PWA support:
- Add a `manifest.json` with app icons
- Register a service worker for offline caching
- Add install prompt handling
