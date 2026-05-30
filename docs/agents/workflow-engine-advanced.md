# Advanced Agent Workflow Engine

The Advanced Agent Workflow Engine enables complex, non-linear agentic processes using Directed Acyclic Graphs (DAGs). It supports conditional branching, parallel execution (fan-out/fan-in), and nested sub-workflows.

## Core Concepts

### Workflow Definition
A workflow is defined by a set of **Nodes** and **Edges**.

- **Nodes**: Represent individual steps or control points (tasks, conditions, parallel groups).
- **Edges**: Represent the flow between nodes, optionally with conditional expressions.

### Node Types

| Type | Description |
|------|-------------|
| `task` | Executes a specific unit of work or agent action. |
| `condition` | Evaluates logic to decide the next path. |
| `parallel_fanout` | Starts multiple branches in parallel. |
| `fanin_join` | Synchronizes multiple parallel branches. |
| `subworkflow` | Executes another workflow as a child process. |
| `approval` | Pauses for human intervention. |
| `timer` | Pauses execution for a specified duration. |
| `webhook_wait` | Waits for an external webhook signal. |

## Branching & Conditions

Conditions can be based on:
- **Policy Results**: `{"type": "policy_result", "target": "guardrail_1", "operator": "eq", "value": "pass"}`
- **Tool Results**: `{"type": "tool_result", "target": "search_tool", "operator": "contains", "value": "success"}`
- **Memory Values**: `{"type": "memory_value", "target": "user_status", "operator": "eq", "value": "premium"}`
- **Evaluation Scores**: `{"type": "eval_score", "target": "relevance", "operator": "gt", "value": 0.8}`
- **Human Approval**: `{"type": "human_approval", "target": "legal_review", "operator": "eq", "value": "approved"}`

## Parallelism (Fan-out/Fan-in)

The engine supports structured parallelism:
- **Parallelism Limit**: Max number of concurrent branches.
- **Timeout**: Per-branch or per-group execution timeout.
- **Failure Policy**:
  - `fail_fast`: Stop the whole group if one branch fails.
  - `continue`: Keep executing other branches.
  - `compensate`: Trigger compensation logic on failure.

## Sub-workflows

Sub-workflows allow for modular and reusable agentic patterns:
- **Versioning**: Child workflows can be pinned to specific versions.
- **Input/Output Mapping**: Parent context is mapped to child inputs, and results are returned to the parent.
- **Traceability**: Sub-workflow runs are linked to the parent for full auditability.

## Persistence & Recovery

- **Event Sourcing**: Every transition and node completion is logged as an event.
- **State Snapshots**: The current active nodes and context are persisted.
- **Recovery**: After a system restart, the engine automatically resumes workflows from the last known state.
- **Deduplication**: Signal consumption and webhook receipts are idempotent.

## Example DAG Definition

```json
{
  "name": "Research and Report",
  "nodes": [
    {"key": "start", "type": "task", "config": {"action": "initialize"}},
    {"key": "search_parallel", "type": "parallel_fanout", "config": {}},
    {"key": "search_web", "type": "task", "config": {"source": "web"}},
    {"key": "search_docs", "type": "task", "config": {"source": "docs"}},
    {"key": "join_search", "type": "fanin_join", "config": {}},
    {"key": "quality_check", "type": "condition", "config": {
      "branches": [
        {"condition": {"type": "eval_score", "target": "relevance", "gt": 0.7}, "target": "generate_report"},
        {"condition": null, "target": "retry_search"}
      ]
    }},
    {"key": "generate_report", "type": "task", "config": {"template": "summary"}},
    {"key": "approval", "type": "approval", "config": {"role": "editor"}}
  ],
  "edges": [
    {"from": "start", "to": "search_parallel"},
    {"from": "search_parallel", "to": "search_web"},
    {"from": "search_parallel", "to": "search_docs"},
    {"from": "search_web", "to": "join_search"},
    {"from": "search_docs", "to": "join_search"},
    {"from": "join_search", "to": "quality_check"},
    {"from": "generate_report", "to": "approval"}
  ]
}
```
