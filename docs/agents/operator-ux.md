# Agentic Operator UX

## Overview

The Admin UI provides a specialized suite of tools for the daily operation, debugging, and promotion of autonomous agents.

## Key Views

### Agentic Operations Dashboard
- Real-time status of agentic platform feature flags (`OBSERVABILITY`, `INCIDENT_RESPONSE`).
- Listing of active agents with their current environment (`draft`, `beta`, `production`).
- Aggregate Risk Score per agent.

### Replay Comparative Analysis
Allows operators to compare a candidate agent run against a stable baseline.
- **Steps Delta**: Highlighting added or removed reasoning steps.
- **Tool Diff**: Changes in tool calling patterns.
- **Cost/Latency Impact**: Quantitative comparison of performance.

### Agent Lineage
A chronological view of an agent's history, including:
- Version bumps and instruction changes.
- Promotion events across environments.
- Evaluation baseline history.

### Incident Drill-down
Detailed investigation view for incidents, correlating execution timelines with error logs and linked traces.
