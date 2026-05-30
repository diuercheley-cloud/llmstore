# Cost-Aware Planning

## Overview
Cost-aware planning enables the platform to estimate the financial impact of agent plans before they are fully executed. This allows for better budget management and optimization of agent workflows.

## Estimation Logic
The `CostAwarePlanner` evaluates several factors for each task in a plan:
- **Tokens**: Estimates the expected token usage based on instructions and step depth.
- **Tool Costs**: Uses the `max_cost_brl` from tool definitions or defaults for unknown tools.
- **Runtime**: Estimates execution time, helping predict potential timeouts or long-running costs.
- **Approval Costs**: Factors in the operational overhead of steps requiring human-in-the-loop (HITL) approval.

## Optimal Plan Selection
When multiple planning candidates are generated (e.g., during complex reasoning), the planner can automatically select the most cost-effective candidate that meets the quality threshold.

## Database Model
Stored in `agent_plan_cost_estimates`:
- `plan_id`
- `estimated_tokens`
- `estimated_tool_cost_brl`
- `estimated_runtime_seconds`
- `estimated_approval_cost_brl`
- `total_estimated_cost_brl`

## Integration
Estimates are automatically generated whenever an `AgentPlan` is created or updated by the `AgentPlanner`.
