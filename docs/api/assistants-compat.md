# Assistants API Compatibility Layer (V1)

The platform provides a compatibility layer for the OpenAI Assistants API. This allows external applications to use familiar concepts like Threads, Messages, and Runs to interact with our agents.

## Feature Flags
- `AGENT_ASSISTANTS_API_ENABLED=true`: Enables the compatibility layer.
- `AGENT_RUNTIME_ENABLED=true`: Required to execute runs.

## Endpoints

### Assistants
- `POST /v1/assistants`: Create a new assistant (maps to `AgentDefinition`).
- `GET /v1/assistants`: List available assistants for the current tenant.

### Threads
- `POST /v1/threads`: Create a new conversation thread.
- `POST /v1/threads/{thread_id}/messages`: Add a message to a thread.
- `GET /v1/threads/{thread_id}/messages`: List messages in a thread.

### Runs
- `POST /v1/threads/{thread_id}/runs`: Create a run for an assistant on a specific thread.
- `GET /v1/threads/{thread_id}/runs/{run_id}`: Retrieve the status and results of a run.

## Mapping to Platform
- **Assistant** maps to `AgentDefinition`.
- **Run** maps to `AgentRun`.
- **Thread & Message** are persisted state managed by the Assistants service.

## Security
- **Tenant Isolation**: All resources are scoped to the `X-Tenant-ID` header.
- **Tool Policy**: Assistants respect the `allowed_tools` defined in their configuration.
- **Memory Policy**: Integration with long-term semantic memory is supported via the assistant's memory policy.

## Usage Example
```python
import httpx

headers = {"X-Tenant-ID": "my-tenant"}
base_url = "http://localhost:8000/v1"

# 1. Create Assistant
assistant = httpx.post(f"{base_url}/assistants", json={
    "name": "Expert Agent",
    "model": "gpt-4",
    "instructions": "You are a helpful assistant."
}, headers=headers).json()

# 2. Create Thread
thread = httpx.post(f"{base_url}/threads", headers=headers).json()

# 3. Add Message
httpx.post(f"{base_url}/threads/{thread['id']}/messages", json={
    "role": "user",
    "content": "Hello, how are you?"
}, headers=headers)

# 4. Create Run
run = httpx.post(f"{base_url}/threads/{thread['id']}/runs", json={
    "assistant_id": assistant['id']
}, headers=headers).json()

# 5. Poll for completion
# ...
```
