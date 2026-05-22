# Execution Replay

Replaying an agent execution allows administrators and compliance officers to trace steps, audit history, and diagnose failures without triggering real-world actions.

## Read-only Replays

When a run is replayed via `POST /agents/runs/{run_id}/replay`:
1. The system checks `AGENT_REPLAY_ENABLED`. If `false`, replay requests are rejected with a controlled error.
2. The runtime loads all recorded steps (`AgentRunStep`) and checkpoints (`AgentRunCheckpoint`) for the run.
3. The runtime walks through each step sequentially, reconstructing the execution trace.
4. **No side effects are executed**: No LLM calls are made, and no tools are run. Replays are entirely read-only simulations that return recorded inputs, hashes, checkpoints, and execution metadata.

This ensures audit trails can be traversed safely in staging, test, and production environments.
