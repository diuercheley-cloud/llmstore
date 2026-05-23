# Operational Deployment Modes

This document details the controlled operational deployment modes introduced in `v2.0.1-agentic-operational-maturity` to govern features and security boundaries in the Agentic AI Platform.

---

## Overview

The platform supports four deployment modes configured via the `DEPLOYMENT_MODE` environment variable. These modes allow gradual activation from local-only air-gapped workloads to highly-scalable enterprise federated clusters.

The valid modes are:
1. `appliance` (Default)
2. `pilot`
3. `production`
4. `enterprise_managed`

---

## Deployment Modes Matrix

| Feature | Appliance | Pilot | Production | Enterprise Managed |
| :--- | :---: | :---: | :---: | :---: |
| **Agentic Runtime** | 🔴 Disabled | 🟢 Enabled | 🟢 Enabled | 🟢 Enabled |
| **Stateful Workflows** | 🔴 Disabled | 🟢 Enabled | 🟢 Enabled | 🟢 Enabled |
| **SaaS Connectors Mode** | 🔴 Disabled | 🟡 Read-only | 🟢 Governed | 🟢 Governed |
| **Connector Writes** | 🔴 Disabled | 🔴 Disabled | 🟢 Allowed | 🟢 Allowed |
| **Write Approvals** | 🔴 Disabled | 🔒 Mandatory | 🟢 Configurable | 🟢 Configurable |
| **Multi-Agent Teams** | 🔴 Disabled | 🔴 Disabled | 🟡 Opt-in | 🟡 Opt-in |
| **Studio Web Console** | 🔴 Disabled | 🟢 Enabled | 🟢 Enabled | 🟢 Enabled |
| **Strict Budgets** | 🔴 Disabled | 🔒 Enforced | 🟢 Optional | 🟢 Optional |
| **Eval Gates** | 🔴 Disabled | 🟡 Optional | 🔒 Mandatory | 🔒 Mandatory |
| **Worker Autoscaling** | 🔴 Disabled | 🔴 Disabled | 🟢 Enabled | 🟢 Enabled |
| **SLO Enforcement** | 🔴 Disabled | 🔴 Disabled | 🟢 Enabled | 🟢 Enabled |
| **Federation / Multi-Cluster** | 🔴 Disabled | 🔴 Disabled | 🔴 Disabled | 🟢 Enabled |
| **Managed Control Plane** | 🔴 Disabled | 🔴 Disabled | 🔴 Disabled | 🟢 Enabled |
| **Enterprise Observability** | 🔴 Disabled | 🔴 Disabled | 🔴 Disabled | 🟢 Enabled |
| **Tenant Isolation** | 🟡 Standard | 🟡 Standard | 🟡 Standard | 🔒 Strict Cryptographic |

---

## Detailed Mode Postures

### 1. Appliance (`DEPLOYMENT_MODE=appliance`)
Designed for strict air-gapped, highly regulated local deployments.
- **Posture**: Strict Air-gapped / Local Only.
- **Constraints**:
  - No background worker tasks are allowed to start.
  - All SaaS external integrations are completely blocked.
  - Runtime, execution plane, and multi-agent options are strictly disabled.

### 2. Pilot (`DEPLOYMENT_MODE=pilot`)
Designed for initial integration and proof-of-concept testing in safe sandboxes.
- **Posture**: Governed Testing / Human-in-the-loop.
- **Constraints**:
  - Runtime is enabled but external connector writes are blocked.
  - Any mutating tool action or memory write requires explicit operator human approval.
  - Strict resource budgets are enforced.

### 3. Production (`DEPLOYMENT_MODE=production`)
For full, high-scale customer production workloads.
- **Posture**: Production Grade / Automatic Evals & SLOs.
- **Constraints**:
  - Runtime and stateful workflows are fully operational.
  - Agent promotion checks are blocked on validation/eval evidence.
  - Background worker autoscale is permitted.
  - Real-time SLO metric thresholds are enforced.

### 4. Enterprise Managed (`DEPLOYMENT_MODE=enterprise_managed`)
For multi-tenant, federated deployments spanning multiple clusters.
- **Posture**: Enterprise Managed / Federated & Strict Isolation.
- **Constraints**:
  - Enables managed control planes and cross-cluster federation.
  - Enforces strict cryptographic tenant data isolation.
  - Deep enterprise tracing and observability are active.

---

## Troubleshooting Coherence

At startup, the control plane checks if manual environment variables override constraints. For example, setting `DEPLOYMENT_MODE=appliance` and `AGENT_RUNTIME_ENABLED=true` simultaneously violates constraints.
- **Blockers**: Fail the operational readiness checks and prevent healthy server reports.
- **Warnings**: Report degraded status.
