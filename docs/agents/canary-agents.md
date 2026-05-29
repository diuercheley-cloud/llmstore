# Canary Agents

## Overview
Canary Agents are a deployment strategy where a new version of an agent is gradually introduced to a small percentage of production traffic. If the canary performs well, its traffic share is increased until it fully replaces the previous version.

## Deployment Lifecycle
1. **Assignment**: Create a `CanaryAssignment` linking the stable agent to the candidate (canary).
2. **Traffic Splitting**: Configure the `traffic_percentage` (e.g., 5% initially).
3. **Monitoring**: Track success rates, tool accuracy, and safety findings for the canary bucket.
4. **Promotion Gate**: Once sufficient evidence is gathered, the canary is promoted to `active` via an administrative approval.

## Safety Guardrails
- **Automated Revert**: If the canary's regression rate exceeds a threshold, traffic is automatically routed back to the stable version.
- **Eval Requirement**: Promotion to production requires passing a mandatory battery of automated evals.

## API Usage
- `POST /admin/agents/{id}/canary/start`: Start a new canary/shadow deployment.
- `POST /admin/agents/{id}/canary/promote`: Finalize promotion to primary agent.
