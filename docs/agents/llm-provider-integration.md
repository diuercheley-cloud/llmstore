# Agent LLM Provider Integration

This document describes how the Agent Executor integrates with LLM providers in the `llm-inference-stack`.

## Overview

The `AgentExecutor` uses an abstraction layer called `AgentLLMProvider` to communicate with LLMs. This allows the system to switch between mocked execution (for testing and evals) and real execution via the platform's internal inference gateway.

## Architecture

The integration is based on the `AgentLLMProvider` interface located at `control_plane/app/services/agents/agent_llm_provider.py`.

### Providers

1.  **MockAgentLLMProvider**: Returns pre-configured or default responses. Used by default in tests and local development.
2.  **GatewayAgentLLMProvider**: The real implementation that calls the internal inference pipeline.

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
| `AGENT_LLM_PROVIDER` | `mock` | Selects the provider implementation (`mock` or `gateway`). |
| `AGENT_REAL_LLM_ENABLED` | `false` | Global switch to enable/disable real LLM calls for agents. |
| `AGENT_LLM_STREAMING_ENABLED` | `false` | (Future) Enables streaming responses for agents. |

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

## Security

- **Prompt Masking**: Raw prompt text is not logged by default; only hashes are stored in step logs.
- **Tenant Isolation**: Each agent run is strictly tied to a `tenant_id`, and the LLM provider verifies client permissions before execution.
- **Policy Enforcement**: Model policies and guardrails are applied at the gateway level.
