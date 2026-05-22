# Agent Promotion Gates

This document outlines the promotion gates process used to activate or promote an agent to `active` (production) status.

## Overview

Promotion gates act as hard automated checks within the agent lifecycle. When an agent activation is requested via `agent_lifecycle.activate_agent`, the system verifies the evaluation history and gate results to ensure the candidate meets strict quality, safety, and regression criteria.

## Configuration & Feature Flags

-   `AGENT_PROMOTION_REQUIRES_EVALS` (Default: `true`): Enforces that promotion to active status requires evaluation checks.
-   `AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE` (Default: `true`): Enforces that a baseline evaluation must exist for the agent.
-   `AGENT_EVAL_REGRESSION_GATE_ENABLED` (Default: `true`): Compares the candidate run against the baseline and fails if quality regresses.

## Promotion Blocker Conditions

The promotion gate will block activation if any of the following failure conditions occur:

1.  **Missing or Stale Baseline**:
    -   If no baseline has been registered for the agent.
    -   If the registered baseline is marked as stale (e.g. after agent definition or tool registration updates).
2.  **Regression**:
    -   If the candidate run's pass rate is lower than the baseline (or fails regression thresholds for latency and cost).
3.  **Safety Assertions Failures**:
    -   **Secret Leaks**: Verification fails if markers like `SECRET_`, `KEY_`, `SECRET_KEY`, or `API_KEY` are detected in outputs or assertion logs.
    -   **Cross-Tenant Isolation Violations**: Verification fails if unauthorized cross-tenant data access is detected or if tenant isolation assertions fail.
    -   **Policy Bypass**: If policy engines are bypassed or `no_policy_denial` assertions fail.
    -   **Prohibited Tool Usage**: If the agent attempts to call a tool not listed in the case's `allowed_tools` list, or fails `tool_not_called` assertions.
4.  **Cost and Steps Budget Exceeded**:
    -   If individual cases exceed their `max_cost_brl` or `max_steps`.
    -   If the entire suite run exceeds the global budget constraints.

## Evaluation Gate Results & Metadata

When the gate runs:
-   It records results in the `AgentEvalGateResult` and `AgentPromotionGateResult` models.
-   It populates metrics such as `tool_misuse_rate`, `policy_denial_rate`, `avg_latency_ms`, `total_cost_brl`, `secret_leak_detected`, `cross_tenant_access_detected`, and `max_steps_exceeded`.

## Markdown Report Generation

Upon evaluating a promotion, the system automatically writes an evaluation report `agent_eval_report.md` in the current working directory. This report includes:

-   **Overall Status**: `PASS` or `FAIL`.
-   **Metadata**: Agent ID, Eval Run ID, LLM Provider, Model ID, and Override details.
-   **Gate Details**: Pass rate, average latency, total cost, tool misuse rates, and safety violation flags.
-   **Regression Diff**: Comparison with the baseline run (pass rate diff, latency diff, and cost diff).
-   **Case-by-Case Results**: Tabular overview showing the name, status, latency, cost, token usage, and assertion messages for each test case.

## Audit Override Mechanism

In emergencies or when regression is expected and accepted, authorized administrators can bypass promotion gate blocks by supplying:
-   `audit_override: true`
-   `override_reason`: A description of why the block is being bypassed.
-   `override_by`: The username of the performing administrator.

This bypass will mark `passed` as `true` on the `AgentPromotionGateResult` and log the override details for compliance auditing.
