# Workflow Signals

Signals are asynchronous messages sent to a running workflow. They are the primary mechanism for waking up a workflow that is in `waiting_signal` state.

## Sending a Signal

Signals can be sent via the Admin API:
`POST /admin/agents/workflows/{id}/run/{run_id}/signal`

```json
{
  "signal_name": "user_input_received",
  "payload": {
    "data": "..."
  }
}
```

## Internal Processing

When a signal is received:
1. It is recorded in `agent_workflow_signals`.
2. If the workflow is in `waiting_signal`, its status is updated to `running`.
3. The next worker to process the run will consume the pending signals.
