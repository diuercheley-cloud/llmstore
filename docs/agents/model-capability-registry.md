---
owner: platform-ops
status: consolidated
---

# Model Capability Registry

## Overview
The Model Capability Registry is a centralized store of performance metrics, costs, and supported features for all models available to the platform.

## Capability Fields
- `model_id`: Unique identifier for the model.
- `provider`: The hosting provider (local, openai, anthropic, etc.).
- `supports_tool_calling`: Boolean indicating native tool call support.
- `supports_json_mode`: Boolean indicating structured output support.
- `context_window`: Maximum tokens the model can handle.
- `cost_input`: Cost per 1,000 input tokens (in BRL).
- `cost_output`: Cost per 1,000 output tokens (in BRL).
- `latency_class`: Expected latency (ultra-low, low, medium, high).
- `quality_tier`: Relative quality ranking (1-5).
- `recommended_step_classes`: List of task types this model excels at.

## Management
Capabilities can be managed via the Admin API:
`GET /admin/agents/routing/capabilities`
