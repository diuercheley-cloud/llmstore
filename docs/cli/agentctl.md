---
owner: platform-ops
status: consolidated
---

# agentctl CLI

The `agentctl` tool is the command-line interface for managing agents on the Kleber AI Platform.

## Commands

### `init`
Scaffold a new agent directory.
```bash
agentctl init my-agent --template support-triage
```

### `validate`
Validate the `agent.yaml` manifest.
```bash
agentctl validate ./my-agent
```

### `register`
Register the agent with the platform.
```bash
agentctl register ./my-agent
```

### `run`
Execute a run for a registered agent.
```bash
agentctl run <agent-uuid> --input '{"query": "test"}'
```

### `eval`
Run evaluation suite for an agent.
```bash
agentctl eval <agent-uuid>
```

### `promote`
Promote an agent to a new environment status.
```bash
agentctl promote <agent-uuid> production
```
