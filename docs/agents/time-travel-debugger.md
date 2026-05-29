# Time-Travel Debugger

## Overview
The Time-Travel Debugger is an advanced diagnostic tool for Agentic AI workflows. it allows developers and operators to "travel back in time" to any step of an agent's execution, inspect the state, modify parameters, and replay the execution path to understand failures or optimize behaviors.

## Key Concepts

### 1. Step Snapshots
The system automatically captures a complete snapshot of the execution environment at every step. This includes:
- **State Hash**: Cryptographic integrity check of the agent's internal state.
- **Memory References**: Links to all cognitive memory items retrieved or updated.
- **Tool Receipts**: Immutable records of external tool calls and their results.
- **Policy Decisions**: Governance engine logs justifying each step.
- **Context Hash**: Snapshot of the prompt and auxiliary data.

### 2. Rewind and Replay
Unlike traditional debuggers, the Time-Travel Debugger creates a **Replay Run**. This is a parallel execution that inherits the state of the original run at step `N`. The original run remains immutable and protected for audit purposes.

### 3. State Editing
In a debug session, operators can manually edit the agent's state (e.g., modifying a tool's output or correcting a memory entry) to test how the agent would respond to different inputs without redeploying code.

### 4. Comparison (Diff)
The `DebugDiff` service provides a structural comparison between the original run and the replay, highlighting divergence in:
- **Step Count**: Did the replay take more or fewer steps?
- **Final Status**: Did the change turn a `failed` run into `completed`?
- **Cost**: Difference in token usage or financial budget.
- **Output Integrity**: Comparing the final synthesized answer.

## Safety and Privacy
- **Redaction**: Raw Chain-of-Thought (CoT) and secrets are masked or redacted in snapshots.
- **Isolaton**: Replays run in a specialized debug tenant by default.
- **Governance**: Every edit and replay is logged in the administrative audit trail.

## API Usage
- `GET /admin/agents/runs/{id}/snapshots`: List all available rewind points.
- `POST /admin/agents/runs/{id}/debug/replay-from-step`: Start a new debug session.
- `POST /admin/agents/debug/{id}/state-edit`: Apply a manual correction to the state.
- `GET /admin/agents/debug/{id}/diff`: Analyze the results of the debug session.
