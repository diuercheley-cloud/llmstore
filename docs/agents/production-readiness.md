# Production Readiness for Agents

Deploying an agent to production requires meeting several governance gates to ensure stability, safety, and accountability.

## Requirements for Activation

To transition an agent to `active` status, the following conditions must be met:

1. **Owner Assigned**: Every production agent must have a designated owner (email or user ID).
2. **Evaluation Baseline**: If `AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE` is enabled, the agent must have a linked `AgentEvalBaseline`.
3. **Approval Signature**: Agents with `high` or `critical` risk levels require an explicit approval signature from an authorized reviewer.
4. **Version Control**: The agent definition must be finalized and approved in the registry.

## Evaluation Baseline

A baseline is established by running an evaluation suite against the agent version and verifying that the results meet the required pass rate. This ensures that:

- Regressions are caught before deployment.
- Security vulnerabilities (like prompt injection) are tested.
- Tool usage is within expected boundaries.
- Costs and latency are monitored.

## Governance Override

In exceptional cases, the baseline requirement can be overridden by an administrator with `SUPER` role by manually populating the `eval_baseline` field in the registry with a justification string, although using the automated framework is strongly preferred.
