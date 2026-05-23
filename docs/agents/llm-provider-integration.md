# Agent LLM Provider Integration

This document describes how the Agent Executor integrates with LLM providers in the `llm-inference-stack`.

## Overview

The `AgentExecutor` uses an abstraction layer called `AgentLLMProvider` to communicate with LLMs. The system supports three explicit modes with strict deployment-mode enforcement — **mock is never used silently**.

## Architecture

The integration is based on the `AgentLLMProvider` interface located at `control_plane/app/services/agents/agent_llm_provider.py`.

### Providers

1.  **MockAgentLLMProvider**: Returns pre-configured or default responses. Used in CI, tests, and local dev. **Blocked in production unless explicitly overridden.**
2.  **GatewayAgentLLMProvider**: Routes through the internal inference gateway pipeline with full model policy, routing, quota, and billing.
3.  **RealAgentLLMProvider**: Direct external provider call, bypassing the internal gateway for GA/enterprise deployments.

### Provider Selection Logic

The `get_agent_llm_provider()` factory function:
1. Reads `AGENT_LLM_PROVIDER` from settings.
2. Validates the provider against the current `DEPLOYMENT_MODE`:
   - `appliance` / `development`: any provider allowed.
   - `pilot`: gateway or real preferred; mock emits a warning.
   - `production` / `enterprise_managed`: mock raises `MockProviderError` unless `AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=true`.
3. Returns the appropriate provider implementation.

### Integration Pipeline

When using the `GatewayAgentLLMProvider`, the following steps are performed:

1.  **Model Resolution**: The `model_id` defined in the `AgentDefinition` is resolved using `model_policy`.
2.  **Tenant Isolation**: The `tenant_id` from the `AgentRun` is used to fetch the corresponding `Client` record, ensuring strict isolation.
3.  **Routing**: The `smart_router` determines the best backend for the request based on availability and priority.
4.  **Quota & Rate Limiting**: The system enforces daily/weekly/monthly token quotas and rate limits defined in the client's billing plan.
5.  **Inference Proxy**: The request is forwarded to the data plane via the `InferenceProxy`.
6.  **Usage Tracking**: Tokens consumed and estimated costs are recorded in the platform's billing and observability systems.

## Configuration

The following feature flags control the LLM provider behavior:

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `AGENT_LLM_PROVIDER` | `mock` | Selects the provider implementation (`mock`, `gateway`, or `real`). |
| `AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION` | `false` | Override to allow mock in production. NOT for GA. |
| `AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION` | `true` | Require gateway/real provider in production mode. |
| `AGENT_REAL_LLM_ENABLED` | `false` | Global switch to enable/disable real LLM calls for agents. |
| `AGENT_LLM_STREAMING_ENABLED` | `false` | (Future) Enables streaming responses for agents. |

## Provider Response Metadata

Every provider response now includes structured metadata:

| Field | Description |
|-------|-------------|
| `provider_type` | `mock`, `gateway`, or `real` |
| `model_id` | The resolved model identifier |
| `backend_id` | The inference backend UUID used |
| `execution_mode` | Deployment mode at time of execution |
| `tokens` | `{prompt: N, completion: N}` |
| `latency` | Total latency in milliseconds |
| `fallback_used` | Whether a route fallback occurred |
| `validation_status` | `mock_bypass`, `validated`, `real_provider` |

This metadata is recorded in the run's `metadata` field and in observability events.

## Observability

The `AgentExecutor` records detailed metadata for each step in the `AgentRunStep` table, including:

- `input_hash`: SHA256 of the prompt.
- `output_hash`: SHA256 of the response.
- `step_metadata`: JSON containing:
    - `backend_id`: The ID of the backend used.
    - `backend_name`: The name of the backend.
    - `prompt_tokens`: Number of input tokens.
    - `completion_tokens`: Number of output tokens.
    - `cost_brl`: Estimated cost of the call in BRL.
    - `provider_type`: Which provider served the request.
    - `validation_status`: Provider validation state.

## Error Handling

| Condition | Error Type | Behavior |
|-----------|-----------|----------|
| Mock in production (no override) | `MockProviderError` | Run fails with clear error message |
| Provider unavailable | `ProviderUnavailableError` | Run fails with "All LLM routes failed" |
| Invalid provider value | `ValueError` | System refuses to start |
| All routes fail | `ProviderUnavailableError` | Routes are exhausted and reported |

## Security

- **Prompt Masking**: Raw prompt text is not logged by default; only hashes are stored in step logs.
- **Tenant Isolation**: Each agent run is strictly tied to a `tenant_id`, and the LLM provider verifies client permissions before execution.
- **Policy Enforcement**: Model policies and guardrails are applied at the gateway level.
- **No Silent Fallback**: Mock is never used as an implicit fallback. Provider selection is explicit and validated against deployment mode.

## See Also

- [LLM Provider Modes](./llm-provider-modes.md) — detailed provider mode reference
- [Readiness Checks](../operations/readiness.md) — LLM provider readiness reporting
- [GA Readiness](../platform/ga-readiness.md) — GA scoring includes LLM provider validation
