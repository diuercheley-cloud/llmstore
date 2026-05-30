# Agent WebSocket Streaming Protocol

Real-time, bidirectional streaming of events and statuses during agent run execution.

## Configuration

Enable the feature flag in your configuration or `.env` file:
```env
AGENT_WEBSOCKET_STREAMING_ENABLED=true
```

## WebSocket Endpoint

```http
WS /v1/agents/runs/{run_id}/stream?token=<api_key>
```

### Authentication
Authentication is completed via query parameters:
*   `token` or `api_key`: A valid, active, and unexpired client API key associated with your tenant.

Clients can only connect to and stream runs belonging to their own tenant (enforcing strict tenant isolation).

## Bidirectional Controls

Clients can send JSON commands over the WebSocket connection to control run execution state:

### Cancel Run
Cancels job execution and releases resource leases.
*   **Request**:
    ```json
    { "command": "cancel" }
    ```
*   **Response**:
    ```json
    { "status": "command_processed", "command": "cancel", "success": true }
    ```

### Pause Run
Pauses execution loop if the run is currently running or queued.
*   **Request**:
    ```json
    { "command": "pause" }
    ```
*   **Response**:
    ```json
    { "status": "command_processed", "command": "pause", "success": true }
    ```

### Resume Run
Resumes job execution and enqueues it back in the execution plane.
*   **Request**:
    ```json
    { "command": "resume" }
    ```
*   **Response**:
    ```json
    { "status": "command_processed", "command": "resume", "success": true }
    ```

## Streamed Events

The stream sends real-time events as they occur in the execution plane.

### Event Format
```json
{
  "event": "string",
  "run_id": "string",
  "timestamp": "iso-datetime",
  "data": {}
}
```

### Supported Events
*   `run.started`: The run execution has started.
*   `step.started`: A new step in the reasoning graph has started.
*   `model.delta`: LLM streaming output chunk.
*   `tool.called`: A tool call execution has started.
*   `tool.completed`: A tool call execution has completed.
*   `approval.required`: Execution is paused waiting for human-in-the-loop approval.
*   `memory.read`: Retrieval has read from agent memories.
*   `policy.denied`: Action blocked by governance policies.
*   `run.completed`: Run execution completed successfully.
*   `run.failed`: Run execution failed with errors.

## Connection Backpressure

Each WebSocket connection implements connection-level backpressure. Events are queued in a bounded buffer. If a client is slow and fails to read messages, the server buffers them for up to `2.0` seconds. If the buffer remains full, updates are dropped to prevent memory overflow.

## Prompt and Secret Sanitization

Payloads are recursively sanitized before they are written to the stream to prevent credential leaks.
*   Keys containing terms like `token`, `secret`, `key`, `password`, `auth`, `db_url`, and `database` are automatically replaced with `"[REDACTED]"`.
*   String values are regex-scanned and redacted if they contain API keys (e.g. OpenAI `sk-...`), Bearer credentials, or database connection strings.
