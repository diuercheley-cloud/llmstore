# Semantic Model Fallback

To increase resilience against provider failures or specific model weaknesses, the platform supports semantic model fallback.

## Fallback Policies

- **JSON Malformed**: If a model repeatedly fails to produce valid JSON, the agent switches to a more capable model (e.g., from `gpt-4o-mini` to `gpt-4o`).
- **Context Length Exceeded**: Switch to a version of the model with a larger context window.
- **Provider Failure**: If a provider is down, switch to an alternative provider (e.g., OpenAI to Anthropic).

## Governance

- `AGENT_SEMANTIC_MODEL_FALLBACK_ENABLED`: Global toggle.
- Fallback must respect the defined budget for the agent run.
- Fallback events are recorded in receipts and audit logs.
