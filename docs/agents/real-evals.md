# Real Agent Evaluations with Controlled Providers

This document describes how the Agent Evaluation Framework supports running evaluations against real, controlled language model providers instead of mock providers, and how safety guarantees are enforced.

## Overview

Historically, agent evaluations in the system relied on the `MockLLMProvider` to ensure fast, deterministic, and free test executions. However, validating agent behavior in production-like environments requires testing with real LLM providers.

To prevent unintended API usage and control cost, the evaluation framework allows configuring real LLM provider execution under strict gates and flags.

## Configuration & Feature Flags

The behavior of evaluation providers is controlled by the following feature flags:

-   `AGENT_EVALS_ENABLED` (Default: `false`): Master toggle for the evaluation suite execution.
-   `AGENT_EVAL_PROVIDER` (Default: `"mock"`): Determines which LLM provider type is resolved. Options are:
    -   `"mock"`: Uses `MockLLMProvider` (default for CI/CD environments).
    -   `"gateway"`: Uses the internal gateway via `GatewayAgentLLMProvider` connected to the controlled inference pipeline.
-   `AGENT_EVAL_REAL_PROVIDER_ENABLED` (Default: `false`): Strict opt-in toggle required to execute real provider calls. If this flag is `false` and the gate resolved to `"gateway"`, any evaluation run will fail immediately unless `allow_paid_provider=True` is explicitly passed (e.g. during manual test overrides).

## Provider Resolution Policy

When an evaluation case runs via `AgentEvalService._run_case`:

1.  **Provider Type Detection**:
    -   Resolves the configured provider using `AGENT_EVAL_PROVIDER`.
2.  **Paid Provider Guard**:
    -   If the resolved provider type is `"gateway"`, it performs a safety check.
    -   If both `allow_paid_provider` (passed programmatically) and `Settings.agent_eval_real_provider_enabled` are `false`, a `ValueError("Paid LLM provider is blocked")` is raised. This prevents unauthorized paid API billing.
3.  **Instantiation**:
    -   `"mock"`: Instantiates `MockLLMProvider` using predefined mock responses.
    -   `"gateway"`: Dynamically imports and instantiates `GatewayAgentLLMProvider` using `InferenceProxy`.
4.  **Metadata Recording**:
    -   The suite execution records the provider type and the resolved agent model ID in the `AgentEvalRun.metadata_json` field. This ensures complete auditability of which models were used.

## CI/CD Pipeline Strategy

To maintain cost control and reliability:
-   **Pull Requests (PRs)**: Evals must run with `AGENT_EVAL_PROVIDER=mock`.
-   **Release Branches**: Gateway evals can be enabled via environment configuration if required.
-   **Manual Runs**: Real paid provider execution is opt-in and typically performed manually by authorized administrators or via scheduled pipelines.

## Evaluation Dataset Structure

Evaluation datasets are versioned and immutable. A dataset version (`AgentEvalDatasetVersion`) specifies:
-   **Golden Tasks**: Core tasks that must pass to prevent promotion.
-   **Allowed & Prohibited Tools**: Constraint boundaries enforcing which tools the agent is permitted or forbidden to call.
-   **Expected Behavior & Safety Assertions**: Checks verifying response contents (e.g. no secret leaks, no policy bypass).
-   **Max Cost & Steps Limits**: Constraints limiting the budget and length of an execution.
