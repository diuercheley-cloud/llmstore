# Agent Model Routing

This document explains how agents select and route requests to LLM backends.

## Model Selection

Each `AgentDefinition` has a `model_id` field. This field specifies the "logical" model that the agent should use (e.g., `gpt-4`, `llama-3-70b`).

When an agent run starts, the `GatewayAgentLLMProvider` uses the `model_policy` service to resolve this `model_id` into an actual registry entry.

### Dynamic Routing

The `smart_router` is responsible for finding available backends for the selected model. Routing is based on:

1.  **Priority**: Backends with lower priority values are tried first.
2.  **Health**: Only backends with a `healthy` state are considered.
3.  **Tenant Configuration**: Some models or backends may be restricted to specific tenants.

## Integration with Gateway

By integrating agents with the standard inference gateway, agents automatically benefit from:

- **High Availability**: Automatic failover between backends.
- **Load Balancing**: Distribution of requests across multiple instances.
- **Backend Heterogeneity**: Seamless switching between local backends (llama.cpp, vLLM) and cloud providers (OpenAI, Anthropic).

## Configuration Example

To configure an agent to use a specific model and ensure it routes correctly:

1.  **Register Model**: Ensure the model is in the `model_registry`.
    ```bash
    # Example model registry entry
    model_id: "agent-best-model"
    provider: "openai"
    ```

2.  **Define Agent**: Set the `model_id` in the agent definition.
    ```json
    {
      "name": "Research Agent",
      "model_id": "agent-best-model",
      "instructions": "..."
    }
    ```

3.  **Enable Integration**: Set the environment variables to use the gateway.
    ```env
    AGENT_LLM_PROVIDER=gateway
    AGENT_REAL_LLM_ENABLED=true
    ```

## Observability of Routing

You can track which backend was used for each agent step by inspecting the `step_metadata` in the `AgentRunStep` records.

```sql
SELECT 
    step_number, 
    step_metadata->>'backend_name' as backend,
    latency_ms 
FROM agent_run_steps 
WHERE run_id = '...';
```
