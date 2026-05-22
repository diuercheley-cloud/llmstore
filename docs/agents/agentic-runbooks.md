# Agentic Runbooks

## CRITICAL: Memory Isolation Violation
- **Severity**: P0
- **Action**: Immediately disable agent via `POST /admin/agents/{id}/disable`.
- **Investigate**: Check `agent_memory_access_events` for unauthorized tenant IDs.

## WARNING: Queue Saturation
- **Severity**: P2
- **Action**: Scale worker replicas to +50%.
- **Investigate**: Check for runaway agents (runs with > 50 steps).
