# Workflow Polling

For external systems that do not support webhooks, stateful workflows can use resilient polling.

## How it works

1. **Job Creation**: A polling job is registered for a workflow run, specifying the `url`, `interval`, and a `stop_condition`.
2. **Persistence**: Polling jobs are stored in the database. Workers process them periodically based on the `next_poll_at` timestamp.
3. **Efficiency**: Between poll intervals, no worker resources are consumed by the workflow.
4. **Resilience**:
   - **Backoff**: If the condition is not met, the next poll is scheduled with an exponential backoff.
   - **Max Attempts**: The job will fail or timeout after a configurable number of attempts.
5. **Completion**: When the `stop_condition` is met, a signal is sent to the workflow run with the final payload.

## Configuration

- `AGENT_WORKFLOW_POLLING_ENABLED`: Global toggle.
- `AGENT_WORKFLOW_DISTRIBUTED_LOCKS_ENABLED`: Recommended for multi-worker environments to prevent duplicate polling.
