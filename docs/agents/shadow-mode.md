# Shadow Mode

## Overview
Shadow Mode allows operators to run a new version of an agent (a "Shadow Agent") in parallel with the stable production version. The shadow agent receives the same real-world input but its output is never delivered to the user, and its actions are restricted to non-destructive operations.

## Key Benefits
- **Risk-Free Evaluation**: Test new models, prompts, or tool configurations against real production traffic without impacting user experience.
- **Performance Parity**: Compare latency and cost between the stable and shadow versions.
- **Divergence Detection**: Identify cases where the new version produces significantly different reasoning or results.

## Implementation Details
- **Parallel Execution**: When enabled, the runtime launches a secondary asynchronous task for the shadow agent.
- **Side-Effect Protection**: Shadow agents are flagged in the execution context. Tool adapters and sandboxes use this flag to block destructive operations (e.g., `DELETE` queries, shell execution).
- **Comparison Logic**: The `CanaryComparator` automatically evaluates both runs and flags regressions.

## Configuration
Enable via `AGENT_SHADOW_MODE_ENABLED=true`.
Monitor comparisons via `GET /admin/agents/{id}/canary/comparisons`.
