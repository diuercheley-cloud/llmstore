---
owner: platform-ops
status: consolidated
---

# Delegated Identity and Token Exchange

Sovereign delegated identities and user grants form the backbone of security boundaries for proactive agents.

## Identity Bindings

To bind a sovereign identity (such as a decentralized identifier or OIDC claim) to an agent, invoke the identity service:

```python
from app.services.agents.iam.agent_identity import AgentIdentityService

identity_service = AgentIdentityService(db)
await identity_service.bind_identity(
    tenant_id="tenant-a",
    agent_id=agent_uuid,
    identity_provider="sovereign",
    external_id="did:key:z6MkuS"
)
```

> [!WARNING]
> Write actions (e.g. creating issues, posting messages, updating records) on SaaS connectors are blocked for any agent without a bound identity.

## User Delegated Grants

A user delegates permissions to an agent to act on their behalf by creating an `AgentTokenGrant`.

- **Endpoint**: `POST /admin/agents/{id}/token-grants`
- **Request Body**:
  ```json
  {
    "tenant_id": "tenant-a",
    "user_id": "user-123",
    "connector_id": "github",
    "scopes": ["repo", "user"],
    "expires_at": 1782345600
  }
  ```

To revoke a grant immediately:
- **Endpoint**: `DELETE /admin/agents/{id}/token-grants/{grant_id}`

## On-Behalf-Of (OBO) Token Exchange

To generate an expiring, connector-scoped delegated token, the agent performs a token exchange using the user's grant:

- **Endpoint**: `POST /admin/agents/{id}/tokens/exchange`
- **Request Body**:
  ```json
  {
    "tenant_id": "tenant-a",
    "user_id": "user-123",
    "connector_id": "github",
    "requested_scopes": ["repo"],
    "expires_in_seconds": 3600
  }
  ```

The endpoint validates the user grant scope coverage and returns a raw token string (prefixed with `agt_`), which the agent can then supply to the connector's execution loop.
