# Agent Sessions and Threads

## Overview

Agent Sessions provide a **persistent, stateful conversation abstraction** for agentic
workloads. Instead of stateless runs where each invocation starts fresh, sessions
maintain conversation history, automatic summarization, retention policies, and cross-run
context.

## Concepts

### Session

A **Session** is the top-level container for a conversation between a user and an agent.
It persists across multiple runs and maintains:

- **Conversation history** — all messages across runs
- **State** — active, archived, deleted
- **Metadata** — key-value store for custom attributes
- **Retention policy** — configurable TTL for messages and summaries
- **Automatic summarization** — triggered when message count exceeds threshold

### Thread

A **Thread** is a linear sequence of messages within a session. Every session starts
with one default thread. Additional threads can be created for branching conversations.

### Message

A **Message** represents a single turn in the conversation. Each message has:
- `role`: `user` | `assistant` | `system` | `tool`
- `content`: the text payload
- `content_hash`: SHA-256 fingerprint
- `run_id`: optional link to the AgentRun that produced it

### Session Run Link

When a run is started within a session, an `AgentSessionRun` record links the run to
the session. The user message is automatically recorded as a session message, and the
run's `session_id` field references the session.

### Summary

When a session exceeds 50 messages, automatic summarization can be triggered. Summaries
condense earlier parts of the conversation to fit within token limits while preserving
key context.

## Data Model

### Tables

| Table | Purpose |
|-------|---------|
| `agent_sessions` | Top-level session container |
| `agent_conversation_threads` | Linear message sequences within sessions |
| `agent_thread_messages` | Individual conversation turns |
| `agent_session_runs` | Links between sessions and AgentRuns |
| `agent_session_summaries` | Auto-generated conversation summaries |

### Key Fields

All tables include standard `id` (UUID PK), `created_at`, and `updated_at` fields.

**agent_sessions:**
- `tenant_id` — multi-tenant isolation key
- `agent_id` — FK to agent_definitions
- `user_id` — optional end-user identifier
- `status` — `active` | `archived` | `deleted`
- `summary` — cached text of the latest conversation summary
- `retention_policy` — JSON with `retention_days`, `keep_summaries`, etc.
- `last_message_at` — indexed timestamp for ordering

**agent_thread_messages:**
- `session_id` — denormalized FK for efficient queries
- `thread_id` — FK to conversation_threads
- `run_id` — optional FK to agent_runs
- `role` — `user` | `assistant` | `system` | `tool`
- `content` — the message text
- `content_hash` — SHA-256 for deduplication

## API Endpoints

All endpoints require client authentication via API key.

### Create Session

```
POST /v1/agents/{agent_id}/sessions
```

Creates a new session for the given agent. Automatically creates the default thread.

**Request body:**
```json
{
  "title": "Project discussion",
  "metadata": {"source": "web"},
  "retention_policy": {"retention_days": 90}
}
```

### List Sessions

```
GET /v1/agents/sessions?agent_id=...&status=active&limit=50&offset=0
```

Returns sessions scoped to the authenticated tenant.

### Get Session

```
GET /v1/agents/sessions/{session_id}
```

### Add Message

```
POST /v1/agents/sessions/{session_id}/messages
```

**Request body:**
```json
{
  "role": "user",
  "content": "What is the weather today?",
  "run_id": null,
  "metadata": {}
}
```

### Get Messages

```
GET /v1/agents/sessions/{session_id}/messages?limit=100&offset=0
```

Returns messages in chronological order.

### Start Run in Session

```
POST /v1/agents/sessions/{session_id}/runs
```

**Request body:**
```json
{
  "input_text": "What is the weather today?"
}
```

Creates an AgentRun linked to the session, records the user message, and returns the
run ID. The run can then be tracked via the standard run endpoints or WebSocket stream.

### Update Session

```
PATCH /v1/agents/sessions/{session_id}
```

**Request body:**
```json
{
  "title": "Updated title",
  "status": "archived",
  "metadata": {"key": "value"}
}
```

### Delete Session

```
DELETE /v1/agents/sessions/{session_id}
```

Cascades to all threads, messages, run links, and summaries.

## Context Building

The `SessionContextBuilder` assembles conversation history for LLM context injection:

- **Redacts secrets** — API keys, tokens, passwords masked as `[REDACTED]`
- **Redacts PII** — email addresses, phone numbers masked
- **Injects summaries** — prepends latest summary as system message
- **Token budget** — truncates history to fit within `max_tokens_estimate`

### Usage

```python
from app.services.agents.sessions import SessionContextBuilder

builder = SessionContextBuilder(db)
context = await builder.build_context(
    session_id=session_id,
    max_messages=50,
    include_summary=True,
    redact_secrets=True,
    redact_pii=True,
    max_tokens_estimate=4096,
)

messages = await builder.build_context_for_llm(
    session_id=session_id,
    include_summary=True,
    system_prompt="You are a helpful assistant.",
)
# messages is a list of {"role": ..., "content": ...} ready for LLM API
```

## Retention Policies

Sessions support configurable retention policies:

```json
{
  "retention_days": 90,
  "keep_summaries": true
}
```

- `retention_days`: messages older than this are deleted (default: 90)
- `keep_summaries`: if `true`, summaries are preserved even when messages are deleted

The `SessionHistoryPolicyService.apply_retention_policies()` method scans all active
and archived sessions and applies the configured policy. It supports a `dry_run` mode.

## Tenant Isolation

All session operations are scoped by `tenant_id`. The `AgentSessionService.get_session()`
method always filters by both `session_id` and `tenant_id`, ensuring tenant A cannot
access tenant B's sessions.

## Running with Sessions via the Existing API

To start a run with session context using the existing v1 API:

```http
POST /v1/agents/{agent_id}/runs
Content-Type: application/json

{
  "input_text": "Hello!",
  "session_id": "uuid-of-session"
}
```

When `session_id` is provided, the run is automatically linked to the session, the
user message is recorded in the session history, and `last_message_at` is updated.

## WebSocket Integration

The WebSocket manager now supports `broadcast_to_session()` to send events to all
connections listening to any run within a session.
