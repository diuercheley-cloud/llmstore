---
owner: platform-ops
status: consolidated
---

# Event Triggers Configuration

Event Triggers define the binding between an event source and the execution of a specific agent.

## Trigger Configuration

A trigger record consists of:
- `agent_id`: The ID of the target agent to execute.
- `source_id`: The event source linked to this trigger (optional).
- `trigger_type`: The identifier representing when the trigger fires (e.g. `on_webhook`, `on_schedule`, `on_readiness_degraded`, `on_cost_threshold`, `on_security_event`).
- `rate_limit`: Maximum number of trigger firings allowed per hour (enforced automatically via previous deliveries).
- `budget`: The maximum aggregate cost (in BRL) allowed for runs initiated by this trigger. If the sum of `estimated_cost_brl` of all runs associated with this trigger exceeds the budget, further firings are blocked.
- `is_paused`: Paused triggers immediately reject incoming events.

## Admin API Endpoints

All admin endpoints require the `X-Admin-Token` header.

### 1. Create Event Source
- **Endpoint**: `POST /admin/agents/event-sources`
- **Payload**:
  ```json
  {
    "type": "webhook",
    "config": {},
    "tenant_id": "my-tenant"
  }
  ```

### 2. Create Event Trigger
- **Endpoint**: `POST /admin/agents/event-triggers`
- **Payload**:
  ```json
  {
    "agent_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "trigger_type": "on_webhook",
    "config": {
      "secret": "my-shared-secret",
      "signature_header": "X-Hub-Signature-256"
    },
    "rate_limit": 10,
    "budget": 50.0,
    "tenant_id": "my-tenant"
  }
  ```

### 3. List Event Triggers
- **Endpoint**: `GET /admin/agents/event-triggers`

### 4. Pause Trigger
- **Endpoint**: `POST /admin/agents/event-triggers/{trigger_id}/pause`

### 5. Resume Trigger
- **Endpoint**: `POST /admin/agents/event-triggers/{trigger_id}/resume`

### 6. List Deliveries
- **Endpoint**: `GET /admin/agents/event-deliveries`
