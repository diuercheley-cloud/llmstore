---
owner: platform-ops
status: active
---

# Agentic Production-ON Validation

## Problem

The standard `agentic-readiness` target passes when the agentic runtime is
`disabled` (safe default). This means a deployment can pass readiness without
ever validating that the runtime actually executes agent runs in production.

## Solution

The **agentic-production-on** validation target requires the runtime to be fully
live. It creates a real test agent, starts a run, verifies worker processing,
tool execution, memory I/O, knowledge graph queries, eval execution, and trace
receipt generation.

## Profile

```
config/deployment-profiles/agentic-production-on.yaml
```

Key flags:

| Flag | Value | Purpose |
| :--- | :---: | :--- |
| `AGENT_RUNTIME_ENABLED` | `true` | Runtime live |
| `AGENT_WORKER_ENABLED` | `true` | Worker processes jobs |
| `AGENT_TOOL_EXECUTION_ENABLED` | `true` | Tool execution allowed |
| `AGENT_EVALS_ENABLED` | `true` | Eval gateway active |
| `AGENT_MCP_CLIENT_ENABLED` | `true` | MCP client ready (mock) |
| `AGENT_KNOWLEDGE_GRAPH_ENABLED` | `true` | KG queries work |
| `AGENT_REASONING_LOOP_ENABLED` | `true` | Reasoning loop active |
| `AGENT_REAL_LLM_ENABLED` | `false` | No real provider calls |
| `AGENT_PAID_PROVIDERS_ENABLED` | `false` | No paid provider calls |
| `AGENT_DESTRUCTIVE_TOOLS_ENABLED` | `false` | Destructive tools blocked |
| `AGENT_MCP_EXTERNAL_NETWORK_ENABLED` | `false` | External network blocked |
| `AGENT_TOOL_SANDBOX_ENABLED` | `true` | Sandbox enforced |
| `AGENT_HUMAN_APPROVAL_ENABLED` | `true` | Human approval required |

## How to Run

```bash
# Run the validation
make agentic-production-on-readiness

# Or directly:
bash scripts/validate-agentic-production-on.sh
```

## What Is Validated

1. **Profile** — confirms `AGENT_RUNTIME_ENABLED=true` in the profile YAML
2. **Agent creation** — creates a test agent via `POST /admin/agents`
3. **Run start** — starts a run via `POST /admin/agents/runs`
4. **Worker** — verifies at least one worker is active
5. **LLM provider** — confirms mock/gateway mode (no real LLM leaks)
6. **Tool execution** — executes `echo` tool and validates output
7. **Memory R/W** — writes a key/value and reads it back
8. **KG query** — queries the knowledge graph
9. **Eval gateway** — runs an eval
10. **Trace + receipt + finalization** — verifies trace/receipt endpoints and run status

## How to Distinguish from Safe-Default

| Criterion | `agentic-readiness` | `agentic-production-on-readiness` |
| :--- | :--- | :--- |
| Runtime `disabled` | PASS (safe default) | FAIL |
| No worker | WARN | FAIL |
| No agent creation | Not checked | FAIL |
| No tool execution | Not checked | FAIL |
| No memory I/O | Not checked | FAIL |
| No KG query | Not checked | FAIL |
| No eval | Not checked | FAIL |
| No trace/receipt | Not checked | FAIL |

## Test Cases

### TC-1: production-on profile validates a real safe run
1. Load `agentic-production-on` profile
2. Run `make agentic-production-on-readiness`
3. Expected: PASS, all 10 checks green

### TC-2: runtime disabled does NOT satisfy this target
1. Load profile with `AGENT_RUNTIME_ENABLED=false`
2. Run `make agentic-production-on-readiness`
3. Expected: FAIL (check 1)

### TC-3: missing worker fails
1. Scale workers to 0
2. Run `make agentic-production-on-readiness`
3. Expected: FAIL (check 4)

### TC-4: silent tool mock fails
1. Disable tool execution (`AGENT_TOOL_EXECUTION_ENABLED=false`)
2. Run `make agentic-production-on-readiness`
3. Expected: FAIL (check 6)

### TC-5: missing receipts fail
1. Disable tracing (`AGENT_TRACE_ENABLED=false`)
2. Run `make agentic-production-on-readiness`
3. Expected: FAIL (check 10)

## Artifacts

Results are written to:

```
artifacts/readiness/agentic-production-on.md
```

This file contains a markdown table with all check results and a PASS/FAIL
verdict.
