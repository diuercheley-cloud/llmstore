---
owner: platform-ops
status: consolidated
---

# Production Readiness for Agentic Runtime

## Overview

Autonomous agents require a specialized readiness framework to ensure safety and performance in production.

## Readiness Gates

- **Heartbeat**: At least 3 healthy workers must be active.
- **Queue Health**: p95 wait time < 5 seconds.
- **Incident Backlog**: Zero open critical incidents.
- **Evaluation Baseline**: All agents must have a passed baseline within the last 30 days.

## Verification

Run the automated readiness suite:
```bash
make agentic-readiness
```
