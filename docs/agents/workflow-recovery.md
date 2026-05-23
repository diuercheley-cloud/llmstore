# Workflow Recovery

The Workflow Engine is designed to handle worker failures gracefully.

## Automatic Recovery

The `WorkflowRecoveryService` periodically scans for workflow runs that are stuck in the `running` state.

- **Timeout**: By default, a run is considered stuck if it hasn't been updated for 10 minutes.
- **Action**: Stuck runs are reset to `retry_scheduled` or `pending`.
- **Auditing**: Every recovery action is logged as a `recovery` event in the workflow history.

## Manual Recovery

Admins can manually retry or reset workflows via the API if needed.
