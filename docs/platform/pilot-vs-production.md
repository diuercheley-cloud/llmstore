# Pilot vs. Production Deployment Modes

This document provides a detailed comparison between `pilot` and `production` modes to help operators safely transition agentic platform workloads.

---

## Core Focus Comparison

| Area | Pilot Mode (`pilot`) | Production Mode (`production`) |
| :--- | :--- | :--- |
| **Operational Goal** | Sandbox evaluation and developer testing. | Mission-critical business execution. |
| **Primary Safety Gate** | Mandatory Human Approval (Human-in-the-loop). | Automated Evaluation & SLO Enforcement. |
| **Connector Access** | Read-Only (Safe-by-default SaaS). | Read/Write (Governed & Audited). |
| **Cost Control** | Strict Budgets (Aggressive limits). | Configurable Budgets & SLO Classes. |
| **Scaling** | Local embedded worker execution. | Distributed worker autoscaling. |

---

## Budget Enforcement

### Pilot Mode Budget Rules
When `DEPLOYMENT_MODE=pilot` is active, the setting `AGENT_STRICT_BUDGETS` defaults to `true`. This instructs the budget engine to apply strict cost containment:
- **Maximum Step Limits**: Runs are bounded to a maximum number of steps.
- **Maximum Cost (BRL)**: Prohibits expensive model calls from accumulating high usage.
- **Strict Approval Wait**: Approvals expire and cancel runs quickly if operators do not respond.

### Production Mode Budget Rules
In `production` mode:
- Budgets are mapped dynamically using SLA classes (`config/agent-slo-classes.yaml`).
- Overrides are allowed on a per-tenant/per-client basis.
- Exceeding budget generates alerts and escalations but does not immediately kill critical production tasks unless configured.

---

## Connector Permissions & Writes

- **Pilot Connectors**:
  - `AGENT_CONNECTOR_WRITE_ENABLED` is hard-locked to `false`.
  - Connectors (Slack, Jira, Confluence, Salesforce) can only call read-only endpoints (e.g. searching/fetching files).
  - External network connectivity is allowed but writes are blocked.

- **Production Connectors**:
  - `AGENT_CONNECTOR_WRITE_ENABLED` defaults to `true`.
  - Write calls are allowed but mapped under audit logs and policy guardrails.
  - Integration tokens are governed by automated credential rotation.

---

## Promotion & Evaluation Gates

- **Pilot**:
  - Flexible testing allows developers to prototype without complete validation baseline datasets.
  - Evaluation results are advisory.

- **Production**:
  - `AGENT_PROMOTION_REQUIRES_EVALS` and `AGENT_EVAL_REGRESSION_GATE_ENABLED` are locked to `true`.
  - The CI/CD runtime refuses to promote or start agents that do not have signed regression test evidence or baseline eval metrics.
  - Failed gates trigger automatic rollbacks.
