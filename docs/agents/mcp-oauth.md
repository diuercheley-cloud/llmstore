# MCP OAuth Identity Delegation

This document describes how agents call external Model Context Protocol (MCP) servers using delegated OAuth2 user/tenant identities instead of global stack credentials.

## Overview

The stack supports delegating user credentials to external MCP servers dynamically. Instead of configuring a single global token for services like GitHub or Slack, each agent execution resolves the correct identity based on the active user and tenant context.

### Features
* **User-Delegated Grants:** Access tokens linked to individual users, ensuring least-privilege access.
* **Tenant Service Principals:** Fallback to tenant-level credentials for shared tools/servers.
* **Global Fallback Control:** Only allows global credential usage when explicitly enabled.
* **Fine-Grained Scope Policies:** Tenant admins can limit tool executions by enforcing scope requirements and access limits.

## API Endpoints

### Register OAuth Client
Configure external OAuth2 servers trusted by the stack.
* **Route:** `POST /admin/agents/mcp/oauth/clients`
* **Request Body:**
  ```json
  {
    "tenant_id": "tenant-1",
    "name": "GitHub OAuth Client",
    "client_id": "gh_client_123",
    "client_secret": "gh_secret_super_secret",
    "auth_url": "https://github.com/login/oauth/authorize",
    "token_url": "https://github.com/login/oauth/access_token",
    "default_scopes": ["read:user", "repo"]
  }
  ```

### Manage Delegated Grants
Link an access token to a user and tenant for specific MCP servers.
* **Route:** `POST /admin/agents/mcp/oauth/grants`
* **Request Body:**
  ```json
  {
    "tenant_id": "tenant-1",
    "user_id": "user-456",
    "mcp_server": "github-mcp",
    "access_token": "user_access_token_here",
    "refresh_token": "user_refresh_token_here",
    "scopes": ["repo"],
    "expires_at": "2026-12-31T23:59:59Z"
  }
  ```
* **Revoke Grant:** `DELETE /admin/agents/mcp/oauth/grants/{id}?tenant_id={tenant_id}`

### Token Exchange
Exchange a user's subject token for an internally managed, scoped token.
* **Route:** `POST /admin/agents/mcp/oauth/token-exchange`
* **Request Body:**
  ```json
  {
    "tenant_id": "tenant-1",
    "subject_token": "user_access_token_here",
    "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    "mcp_server": "github-mcp",
    "requested_scopes": ["repo"]
  }
  ```

### Auditing
View the policy decision history and audit events.
* **Route:** `GET /admin/agents/mcp/oauth/audit`

## Security Considerations

1. **Token Protection:** Raw tokens are never logged. Responses for listing/getting clients and grants redact sensitive attributes (e.g. returning `[REDACTED]`).
2. **Tenant Isolation:** Grants are strictly separated. Tenants can only query/revoke/use their own grants. Tenant A is blocked from using Tenant B's credentials.
3. **Scope Enforcement:** Scope policies block tool calling if the active grant does not satisfy the configured scope constraints.
