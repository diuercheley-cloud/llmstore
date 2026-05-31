# User Agent Chat UI

## Overview

The User Agent Chat UI provides a high-fidelity, real-time interface for end-users to interact with agents. It replaces basic playgrounds with a production-ready experience featuring persistent sessions, streaming responses, and detailed activity tracking.

## Components

### Agent Chat Page (`AgentChat.tsx`)
The main orchestrator that manages:
- Authentication state (Client API Token).
- Agent selection.
- Session switching.
- WebSocket lifecycle for real-time updates.

### Session List (`SessionList.tsx`)
Allows users to browse their previous conversations with a specific agent, delete old sessions, or start a new "New Thread".

### Message List (`MessageList.tsx`)
Renders the conversation history. It handles:
- User messages.
- Agent responses (including Markdown and code blocks).
- Streaming deltas for low-latency feedback.
- Tool activity indicators.

### Composer (`Composer.tsx`)
The rich input area. Features:
- Multi-line auto-expanding textarea.
- Shift+Enter for new lines, Enter to send.
- Support for file/image attachments (Multimodal-ready).
- Run cancellation during active streaming.

### Tool Activity Timeline (`ToolActivityTimeline.tsx`)
A visual timeline of what the agent is doing "under the hood" during a run:
- **Tool Calls**: Shows which tools are being invoked and their status.
- **Memory Access**: Indicates when the agent reads from short-term or long-term memory.
- **Approvals**: Highlights when a human-in-the-loop (HITL) intervention is required.

## Features

- **Real-time Streaming**: Uses WebSockets to stream deltas directly to the UI, providing immediate feedback as the agent thinks.
- **Persistent State**: Conversations are stored on the server via the Session API. Users can close the app and resume later.
- **Tenant Isolation**: The UI respects the API token's tenant scope. Users only see agents and sessions authorized for their client key.
- **Responsive Design**: Mobile-friendly sidebar and layout, ready for PWA wrapping.

## WebSocket Protocol

The UI listens for the following events on `ws://.../v1/agents/runs/{run_id}/stream`:

| Event | Action |
|-------|--------|
| `text_delta` | Appends text to the current response buffer. |
| `tool_call` | Adds a tool activity item to the timeline. |
| `memory_read`| Shows a memory access event. |
| `step_completed` | Updates activity status and optionally provides output. |
| `run_completed` | Triggers a final message history reload and stops streaming mode. |
| `run_failed` | Displays an error banner with the failure reason. |
