---
owner: platform-ops
status: consolidated
---

# Agentic Chaos Engineering

## Principles

We intentionally inject failures into the agentic runtime to prove recovery mechanisms.

## Scenarios

- **`worker_crash`**: Kill random workers. Proves lease recovery and re-queueing.
- **`lease_expiry`**: Manually expire active leases. Proves that stuck runs don't orphan resources.
- **`tool_timeout`**: Simulate slow tools. Proves that agents respect global timeout policies.

## Automation

Chaos experiments can be triggered via `agentic-chaos-run.sh`.
