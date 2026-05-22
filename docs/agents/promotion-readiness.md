# Promotion Readiness Checklist

## Overview

This document defines **everything that must happen** before an agent can be promoted to production. It covers the full agent lifecycle, gate requirements at each transition, baseline management, and CI integration.

No agent reaches production by accident. Every transition is gated, audited, and traceable.

---

## Lifecycle States

Agents progress through a defined set of states. Each transition has specific requirements that must be met before the system allows the state change.

```
┌─────────┐     ┌────────┐     ┌──────────┐     ┌────────┐
│  draft  │────▶│ review │────▶│ approved │────▶│ active │
└─────────┘     └────────┘     └──────────┘     └────────┘
                                                     │
                                                     ▼
                                                ┌────────┐
                                                │ paused │
                                                └────────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ deprecated  │
                                              └─────────────┘
                                                     │
                                                     ▼
                                              ┌──────────┐
                                              │ archived │
                                              └──────────┘
```

| State | Description |
|-------|-------------|
| `draft` | Initial state. Agent is being developed and configured. |
| `review` | Agent has been submitted for peer review. |
| `approved` | Agent has been reviewed and approved for production. |
| `active` | Agent is live in production, serving requests. |
| `paused` | Agent is temporarily disabled (e.g., for investigation). |
| `deprecated` | Agent is marked for retirement. No new activations allowed. |
| `archived` | Agent is permanently retired. Read-only. |

---

## Gate Requirements at Each Transition

### `draft` → `review`

**Requirement:** At least one completed evaluation dry-run.

The dry-run does not need to pass — its purpose is to ensure the developer has seen the evaluation results and understands the agent's current behavior.

| Check | Required | Details |
|-------|----------|---------|
| Completed eval dry-run | ✅ | Run `make agent-evals AGENT_ID=<id>` at least once. |
| Eval must pass | ❌ | Dry-run results are informational at this stage. |
| Owner set | ❌ | Not required until activation. |

```bash
# Run evaluation dry-run
make agent-evals AGENT_ID=agent-payment-v2

# Submit for review
curl -X POST /admin/agents/agent-payment-v2/submit-review
```

**Failure example:**

```json
{
  "error": "Cannot submit for review: no evaluation dry-run found.",
  "hint": "Run 'make agent-evals AGENT_ID=agent-payment-v2' first."
}
```

---

### `review` → `approved`

**Requirement:** Evaluation baseline must exist and **not be stale**. High/critical risk agents need an approval signature.

| Check | Required | Details |
|-------|----------|---------|
| Evaluation baseline exists | ✅ | Set via `POST /admin/agent-evals/baselines`. |
| Baseline is not stale | ✅ | Baseline invalidates if `instructions`, `allowed_tools`, or `memory_enabled` change. |
| Approval signature (high/critical risk) | ✅ | Required for agents tagged as high or critical risk. |
| Approval signature (low/medium risk) | ❌ | Not required but recommended. |

```bash
# Set evaluation baseline
curl -X POST /admin/agent-evals/baselines \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-payment-v2",
    "eval_run_id": "run-x1y2z3"
  }'

# Approve agent
curl -X POST /admin/agents/agent-payment-v2/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "reviewer@company.com"
  }'
```

**Failure example:**

```json
{
  "error": "Cannot approve: evaluation baseline is stale.",
  "stale_reason": "Field 'instructions' was modified after baseline was set.",
  "hint": "Re-run evals and set a new baseline via POST /admin/agent-evals/baselines."
}
```

---

### `approved` → `active`

**Requirement:** Owner set, evaluation baseline valid, promotion gate verification passed (or `audit_override`).

This is the most critical transition. The full promotion gate runs all checks:

| Check | Required | Details |
|-------|----------|---------|
| Owner set | ✅ | Agent must have an assigned owner. |
| Evaluation baseline valid | ✅ | Must exist and not be stale. |
| Gate result: `PASSED` | ✅ | All threshold checks passed (pass_rate, tool misuse, policy denial, latency, cost, max_steps, secrets, cross-tenant). |
| Regression result: `PASSED` | ✅ | No metric regressions compared to baseline. |
| Baseline check: `PASSED` | ✅ | Baseline exists and is current. |
| **OR** `audit_override` | ✅ | Emergency bypass with `override_reason` and `override_by`. |

```bash
# Run the full promotion gate
make agent-eval-gate AGENT_ID=agent-payment-v2

# Activate the agent (if gate passed)
curl -X POST /admin/agents/agent-payment-v2/activate
```

**Failure example:**

```json
{
  "error": "Cannot activate: promotion gate FAILED.",
  "gate_result": "PASSED",
  "regression_result": "FAILED",
  "baseline_check": "PASSED",
  "failure_reasons": [
    "Regression detected: pass_rate decreased from 1.0 to 0.95"
  ]
}
```

**Override example:**

```bash
curl -X POST /admin/agents/agent-payment-v2/activate \
  -H "Content-Type: application/json" \
  -d '{
    "audit_override": true,
    "override_reason": "Critical hotfix for payment processing. Eval regression is due to flaky test case #17 (JIRA-4521).",
    "override_by": "kleber@company.com"
  }'
```

---

## What Makes a Baseline Stale

A baseline becomes **stale** when the agent's registry entry is modified in ways that could affect its runtime behavior. Specifically, the following field changes invalidate the baseline:

| Field Changed | Staleness Triggered | Rationale |
|---------------|---------------------|-----------|
| `instructions` | ✅ Yes | Core behavior definition changed. |
| `allowed_tools` | ✅ Yes | Available capabilities changed. |
| `memory_enabled` | ✅ Yes | Context handling behavior changed. |
| `description` | ❌ No | Metadata only, does not affect behavior. |
| `owner` | ❌ No | Administrative field, does not affect behavior. |
| `tags` | ❌ No | Organizational field, does not affect behavior. |

When a baseline is stale, the system blocks:

- Agent approval (`review` → `approved`)
- Agent activation (`approved` → `active`)

---

## How to Recover from a Stale Baseline

When your baseline becomes stale, follow these steps:

### Step 1: Re-run the Evaluation Suite

```bash
make agent-evals AGENT_ID=agent-payment-v2
```

This produces a new eval run with results based on the agent's **current** configuration.

### Step 2: Review Results

Check the eval output for any regressions or failures introduced by the configuration change.

### Step 3: Set a New Baseline

```bash
curl -X POST /admin/agent-evals/baselines \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-payment-v2",
    "eval_run_id": "run-new123"
  }'
```

### Step 4: Verify Baseline Status

```bash
curl -X GET /admin/agent-evals/baselines/agent-payment-v2
```

```json
{
  "agent_id": "agent-payment-v2",
  "eval_run_id": "run-new123",
  "stale": false,
  "created_at": "2026-05-22T11:00:00Z",
  "config_hash": "sha256:abc123..."
}
```

---

## Mock LLM Provider

By default, evaluations use `MockLLMProvider` to avoid incurring real LLM costs during testing. The mock provider returns deterministic, pre-configured responses.

| Setting | Default | Description |
|---------|---------|-------------|
| `allow_paid_provider` | `false` | When `false`, evals use `MockLLMProvider`. Set to `true` to use the real LLM provider. |

```bash
# Run evals with mock provider (default)
make agent-evals AGENT_ID=agent-payment-v2

# Run evals with real LLM provider (costs money)
make agent-evals AGENT_ID=agent-payment-v2 ALLOW_PAID=true
```

```json
// API request with paid provider
{
  "dataset_version_id": "dsv-e5f6g7h8",
  "allow_paid_provider": true
}
```

> **💡 Tip:** Use `MockLLMProvider` for CI pipelines and fast iteration. Reserve `allow_paid_provider=true` for pre-production validation runs where you need to test against the actual model.

### When to Use Paid Provider

- **Final validation** before setting a baseline
- **Debugging** unexpected behavior that the mock provider cannot reproduce
- **Performance benchmarking** for latency and cost thresholds

---

## CI Integration

### Makefile Targets

Two Makefile targets are available for CI/CD pipelines:

#### `make agent-evals`

Runs the evaluation suite without gate enforcement. Use this for:
- Development iteration
- Dry-runs before review submission
- CI checks on pull requests

```bash
# Basic usage
make agent-evals AGENT_ID=agent-payment-v2

# With specific dataset version
make agent-evals AGENT_ID=agent-payment-v2 DATASET_VERSION=dsv-e5f6g7h8

# With paid provider
make agent-evals AGENT_ID=agent-payment-v2 ALLOW_PAID=true

# Run all agents
make agent-evals
```

#### `make agent-eval-gate`

Runs the full promotion gate check (eval + regression + baseline). Use this for:
- Pre-activation verification
- Release pipelines
- Nightly gate checks

```bash
# Basic usage
make agent-eval-gate AGENT_ID=agent-payment-v2

# With override (emergency only)
make agent-eval-gate AGENT_ID=agent-payment-v2 \
  OVERRIDE=true \
  OVERRIDE_REASON="Hotfix for JIRA-4521" \
  OVERRIDE_BY="kleber@company.com"
```

### Example CI Pipeline

```yaml
# .github/workflows/agent-promotion.yml
name: Agent Promotion Gate

on:
  push:
    paths:
      - 'agents/**'

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Agent Evaluations
        run: make agent-evals AGENT_ID=${{ env.AGENT_ID }}

      - name: Run Promotion Gate
        run: make agent-eval-gate AGENT_ID=${{ env.AGENT_ID }}
        # This step fails the pipeline if the gate does not pass

      - name: Activate Agent (on main branch only)
        if: github.ref == 'refs/heads/main'
        run: |
          curl -X POST $API_BASE/admin/agents/$AGENT_ID/activate \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}"
```

---

## Promotion Flow Diagram

The complete flow from draft to activation:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Agent Promotion Flow                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────┐    make agent-evals     ┌──────────────┐                         │
│  │ draft │ ──────────────────────▶ │ eval dry-run │                         │
│  └───────┘                         └──────┬───────┘                         │
│                                           │                                  │
│                                           ▼                                  │
│                                    ┌──────────────┐                         │
│                                    │ set baseline │                         │
│                                    └──────┬───────┘                         │
│                                           │                                  │
│                                           ▼                                  │
│                                    ┌──────────┐      approval               │
│                                    │  review  │ ──── signature ────┐        │
│                                    └──────────┘   (high/critical)  │        │
│                                                                     │        │
│                                                                     ▼        │
│                                                              ┌──────────┐   │
│                                                              │ approved │   │
│                                                              └────┬─────┘   │
│                                                                   │          │
│                                           ┌───────────────────────┘          │
│                                           ▼                                  │
│                                  ┌─────────────────┐                        │
│                                  │ promotion gate  │                        │
│                                  │  ├─ gate check  │                        │
│                                  │  ├─ regression  │                        │
│                                  │  └─ baseline    │                        │
│                                  └────────┬────────┘                        │
│                                           │                                  │
│                              ┌────────────┼────────────┐                    │
│                              ▼            │            ▼                    │
│                         ┌────────┐        │     ┌───────────────┐           │
│                         │ PASSED │        │     │    FAILED     │           │
│                         └───┬────┘        │     └───────┬───────┘           │
│                             │             │             │                    │
│                             ▼             │             ▼                    │
│                        ┌────────┐         │     ┌───────────────┐           │
│                        │ active │         │     │ audit_override│           │
│                        └────────┘         │     │  (emergency)  │           │
│                                           │     └───────┬───────┘           │
│                                           │             │                    │
│                                           │             ▼                    │
│                                           │        ┌────────┐               │
│                                           │        │ active │               │
│                                           │        └────────┘               │
│                                           │                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Checklist

Use this checklist to verify an agent is ready for promotion:

- [ ] **Evaluation dataset created** with relevant test cases
- [ ] **Dataset version frozen** (immutable)
- [ ] **Eval dry-run completed** (`make agent-evals`)
- [ ] **Agent submitted for review** (`POST /admin/agents/{id}/submit-review`)
- [ ] **Evaluation baseline set** (`POST /admin/agent-evals/baselines`)
- [ ] **Baseline is not stale** (no changes to `instructions`, `allowed_tools`, `memory_enabled`)
- [ ] **Agent approved** (`POST /admin/agents/{id}/approve`)
- [ ] **Promotion gate passed** (`make agent-eval-gate`)
  - [ ] Pass rate ≥ threshold
  - [ ] Tool misuse rate ≤ threshold
  - [ ] Policy denial rate ≤ threshold
  - [ ] Latency ≤ threshold
  - [ ] Cost ≤ threshold
  - [ ] Steps ≤ threshold
  - [ ] No secret leaks
  - [ ] No cross-tenant access
- [ ] **No regressions** against baseline
- [ ] **Owner assigned** to the agent
- [ ] **Agent activated** (`POST /admin/agents/{id}/activate`)

---

## See Also

- [Evaluation Gates](eval-gates.md) — mandatory quality gates and threshold configuration
- [Evaluation Datasets](eval-datasets.md) — versioned, immutable evaluation case collections
