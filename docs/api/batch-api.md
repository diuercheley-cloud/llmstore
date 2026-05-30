# Batch API (V1)

The Batch API allows you to submit multiple asynchronous workloads (agentic or inference) in a single request. This is ideal for high-volume tasks that do not require immediate responses.

## Feature Flags
- `AGENT_BATCH_API_ENABLED=true`: Enables the Batch API endpoints.
- `AGENT_RUNTIME_ENABLED=true`: Required to execute agentic batch items.

## Endpoints

### Batches
- `POST /v1/batches`: Submit a new batch of tasks.
- `GET /v1/batches/{id}`: Retrieve the status and metadata of a batch.
- `GET /v1/batches/{id}/results`: List the results for all items in a batch.
- `POST /v1/batches/{id}/cancel`: Cancel an in-progress batch.

## Batch Configuration

### Input Format
In the current implementation, `input_data` is passed directly in the request body as a list of objects. In production, this will transition to a JSONL file upload (OpenAI style).

Example item:
```json
{
  "custom_id": "request-001",
  "agent_id": "uuid-here",
  "input_text": "Process this document..."
}
```

### Batch Status
- `validating`: Input data is being checked.
- `in_progress`: Tasks are being executed.
- `completed`: All tasks finished successfully.
- `failed`: The batch failed or a threshold of item failures was reached.
- `cancelled`: The batch was manually cancelled by the user.

## Reliability
- **Partial Failure**: A batch can succeed even if some items fail. Individual item errors are tracked.
- **Retries**: Configurable retry policy per item (forthcoming).
- **Idempotency**: Use `custom_id` to track and deduplicate requests.

## Security
- **Tenant Isolation**: Batches are strictly scoped to the `X-Tenant-ID` header.
- **Budgeting**: (Forthcoming) Limit the total cost/tokens allowed for a single batch.

## Usage Example
```python
import httpx

headers = {"X-Tenant-ID": "my-tenant"}
base_url = "http://localhost:8000/v1"

# 1. Create Batch
batch = httpx.post(f"{base_url}/batches", json={
    "endpoint": "/v1/agents/runs",
    "input_data": [
        {"custom_id": "task-1", "agent_id": "...", "input_text": "Hi 1"},
        {"custom_id": "task-2", "agent_id": "...", "input_text": "Hi 2"}
    ]
}, headers=headers).json()

# 2. Check Status
status = httpx.get(f"{base_url}/batches/{batch['id']}", headers=headers).json()
print(f"Batch status: {status['status']}")

# 3. Get Results
results = httpx.get(f"{base_url}/batches/{batch['id']}/results", headers=headers).json()
for item in results['data']:
    print(f"ID: {item['custom_id']}, Status: {item['status']}")
```
