# Shared Workspaces for Human-Agent Collaboration

The collaborative workspace environment provides a shared context where human operators and autonomous agents can create, update, review, and exchange structured artifacts.

## Feature Flags

Workspaces are controlled by the following feature flag:
- `AGENT_SHARED_WORKSPACE_ENABLED`: Set to `true` to enable workspace creation, listing, and artifact isolation scopes. Defaults to `false`.

## Architecture & Data Scope

- **Isolation**: Workspaces are isolated per tenant (`tenant_id`). Cross-tenant requests are strictly blocked.
- **Ownership**: Each workspace is owned by a specific owner (`owner_id`) and belongs to a single tenant.
- **Artifacts Registry**: Workspaces group related artifacts (such as prompts, code, plans, and reports) that humans and agents collaborate on.

## API Endpoints

- **Create Workspace**
  `POST /admin/agents/workspaces`
  Payload:
  ```json
  {
    "name": "Production Workspace",
    "description": "Shared workspace for prompt deployment",
    "tenant_id": "default"
  }
  ```

- **List Workspaces**
  `GET /admin/agents/workspaces?tenant_id=default`
  Returns all workspaces for the requested tenant.
