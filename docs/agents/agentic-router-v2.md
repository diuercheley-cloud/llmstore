---
owner: platform-ops
status: consolidated
---

# Agentic Router V2

## Overview
Agentic Router V2 is a sophisticated routing system designed to optimize model selection on a per-step basis within an agent's execution loop. By classifying each step (e.g., summarization, code generation, reasoning) and matching it with the most appropriate model based on capabilities, cost, and quality, the router significantly reduces TCO while maintaining high performance for critical tasks.

## Key Features
- **Per-Step Routing**: Instead of using a single model for the entire agent run, each step is routed independently.
- **Step Classification**: Automatically identifies the nature of the task (classification, extraction, reasoning, etc.).
- **Capability-Aware**: Consults a registry of model features (tool calling, JSON mode, context window).
- **Policy-Driven**: Applies configurable policies such as `lowest_cost`, `high_quality`, or `balanced`.
- **Explainable Decisions**: Every routing choice is logged with a detailed explanation of why a specific model was chosen.

## Architecture
The system consists of the following components:
1. **Step Classifier**: Analyzes step metadata and input to determine the `StepClass`.
2. **Model Capability Registry**: Maintains a database of models and their specific strengths and costs.
3. **Cost/Quality Policy Engine**: Filters and ranks models based on the active policy and budget constraints.
4. **Agentic Router**: Orchestrates the flow and records the final decision.

## Usage
Enable the feature via flags:
- `AGENTIC_ROUTER_V2_ENABLED=true`
