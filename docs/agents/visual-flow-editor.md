# Visual Flow Editor

## Usage Guide
The Visual Flow Editor is the primary interface for building multi-step agentic workflows without writing manual JSON plans.

### Node Types
- **Agent**: Represents a model reasoning step with specific instructions.
- **Tool Call**: Executes a registered tool (e.g., `web_search`, `sql_query`).
- **Condition**: Logic gate that branches the flow based on prior outputs.
- **Approval**: Pause execution until a human operator approves the path.
- **Memory Read**: Retrieve long-term or semantic memory items.
- **Handoff**: Delegate the remaining tasks to another specialized agent.
- **Final Response**: Terminal node that synthesizes the output for the user.

### Workflow
1. **Design**: Drag nodes from the palette and connect them using edges.
2. **Configure**: Click on a node to edit its configuration (e.g., tool name, agent instructions).
3. **Validate**: The `DAGValidatorPanel` shows real-time errors (cycles, missing terminals).
4. **Dry-Run**: Use the `Test Runner` to execute the flow with mock side-effects.
5. **Publish**: Save the version and mark it as `active` to promote it to production.

### Security
The editor enforces organizational policies at design time. If a node is configured to perform a high-risk action without proper guards, the validator will block compilation until the policy is satisfied.
