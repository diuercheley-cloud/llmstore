# Agent Operator Runbook

## Handling Incidents

When an incident is fired for an agent, use the following steps:

1. **Acknowledge the Incident:** Use the dashboard or `POST /admin/agents/incidents/{id}/ack`.
2. **Review the Timeline:** Call `GET /admin/agents/runs/{run_id}/timeline` to see what the agent did before the incident.
3. **Analyze Tool Side Effects:** Check if the agent mutated state repeatedly. If yes, consider triggering a tool rollback for that run.
4. **Review Cost:** Call `GET /admin/agents/runs/{run_id}/cost` to verify the financial impact of the run.
5. **Resolve:** Once mitigated (e.g., agent cancelled, policies updated, user contacted), resolve the incident via `POST /admin/agents/incidents/{id}/resolve` and document the fix.

## Troubleshooting Telemetry

If metrics or timelines are missing:
1. Verify the `AGENT_OBSERVABILITY_ENABLED` flag is `true`.
2. Verify the underlying DB is healthy (timeline events are stored locally).
3. If external traces are missing, check `AGENT_TRACE_EXPORT_ENABLED`. By default, it is disabled to prevent accidental data exfiltration.