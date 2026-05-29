# Multi-Agent Governance

## Governance Engine
The `MultiAgentGovernanceService` centralizes the enforcement of collaboration policies.

### Key Policies
1. **Tenant Isolation**: Delegation is strictly forbidden across different `tenant_id` boundaries.
2. **Explicit Delegation**: A source agent can only hand off tasks to a target agent if an explicit `AgentDelegationPolicy` exists and is active.
3. **Approval Boundaries**: High-risk delegations (e.g., involving financial transactions or privileged data access) require manual human-in-the-loop (HITL) approval.
4. **Auditability**: Every handoff and arbitration event is recorded in the trace links, allowing for post-hoc analysis of the "team run".

These controls ensure that complex agentic workflows remain within the safety and compliance guardrails defined by the platform administrators.
