# Cost-Optimized Routing

## Overview
Cost-Optimized Routing leverages the Model Capability Registry and Step Classifier to minimize expenses without sacrificing the quality of critical reasoning steps.

## Policies
- **Lowest Cost**: Always selects the cheapest model that meets the minimum required capabilities.
- **Balanced**: Aims for a high quality-to-cost ratio.
- **High Quality**: Prioritizes the most capable models (Tier 4 or 5) regardless of cost.
- **Local First**: Prefers locally hosted models (Sovereign) to avoid cloud costs and egress.

## Decision Logging
Every routing decision is recorded in the `agent_step_routing_decisions` table, including a full explanation and the budget spent on that particular step. This audit trail allows operators to fine-tune their policies over time.
