# Real Multi-Agent Runtime

The Multi-Agent Runtime has evolved from placeholder-based simulation to real, production-grade delegation. Sub-agents are now executed as authentic runs within the platform.

## Key Features

### 1. Authentic Delegation
Runtimes (Hierarchical, Debate, Dynamic) now use `AgentRuntime.start_run` to execute specialists. This means:
- Sub-agents run through the full `AgentExecutor` loop.
- Guardrails, policies, and tool runners are applied to every sub-task.
- Detailed traces and events are recorded for each member of the team.

### 2. Hierarchical Linking
Every sub-run is linked to its parent via `parent_run_id`. This enables:
- **Trace Correlation**: View the entire tree of execution from the manager down to the deepest specialist.
- **Budget Propagation**: Shared budgets can be enforced across the entire team.
- **Policy Inheritance**: Policies can be applied hierarchically.

### 3. Asynchronous Wait
Managers and dispatchers now asynchronously wait for sub-runs to complete. This ensures that the platform can handle long-running specialist tasks without blocking resources.

### 4. Evidence Aggregation
The final synthesis produced by managers or synthesizers is now based on real output evidence from sub-agents, improving the accuracy and reliability of the team's final response.

## Prohibiting Placeholders

The generation of placeholder text (e.g., "Specialist completed analysis...") is strictly prohibited in production mode. All specialists must be registered agents in the platform.

## Example: Hierarchical Delegation

```python
# Manager delegates to Specialist
sub_run = await agent_runtime.start_run(
    db=db,
    agent_id=specialist_id,
    tenant_id=tenant_id,
    input_text="Perform deep analysis of logs",
    parent_run_id=parent_run_id
)
```
