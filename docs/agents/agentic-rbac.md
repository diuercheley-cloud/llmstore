# Agentic RBAC

## Overview
The agentic plane implements a granular Role-Based Access Control (RBAC) system to separate operational, development, and security responsibilities.

## Roles
- **`agent_viewer`**: Read-only access to agents, tools, memory, and incidents.
- **`agent_operator`**: Can execute agents and manage incidents.
- **`agent_developer`**: Can create/update agents and tools, run evals, and execute runs.
- **`agent_reviewer`**: Can approve agent promotions and review evals.
- **`agent_security_admin`**: Manages environment policies and sensitive tool classes.
- **`agent_tool_admin`**: Manages tool registry and sandboxes.
- **`agent_memory_admin`**: Manages agent memory and data deletion.
- **`agent_approval_reviewer`**: Specific role for human-in-the-loop approvals.
- **`agent_marketplace_admin`**: Manages the agent bundle marketplace.

## Permissions
Permissions are scoped to `agents`, `agent_tools`, `agent_memory`, `agent_evals`, `agent_policies`, and `agent_incidents`.

## Audit
Every denied permission attempt is recorded in `agent_rbac_events` for security auditing.
