---
owner: platform-ops
status: consolidated
---

# Agentic Runtime Rollback Playbook

This playbook outlines the steps to rollback the Agentic Runtime, effectively shutting down agent operations gracefully.

## Objective
To provide a fast and secure method to halt agentic operations without data loss or corruption of stateful workflows.

## Execution
Run the rollback script:
```bash
./scripts/rollback-agentic-runtime.sh
```

## State Changes
During execution, the system will perform the following safe shutdown steps:
- **New Runs:** Paused immediately
- **Queue:** Drained of pending tasks
- **Runtime:** Disabled and reverted to `DEPLOYMENT_MODE=appliance`
- **Workflows:** Preserved (stateful persistent storage)
