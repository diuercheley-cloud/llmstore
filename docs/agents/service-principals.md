---
owner: platform-ops
status: consolidated
---

# Agent Service Principals

Agent Service Principals act as the secure system credentials for agent integrations. In production environments, a Service Principal is required before any connector execution is authorized.

## Creating a Service Principal

To register a service principal for an agent:

- **Endpoint**: `POST /admin/agents/{id}/service-principal`
- **Request Body**:
  ```json
  {
    "description": "Production credentials for GitHub agent"
  }
  ```
- **Response**:
  ```json
  {
    "id": "59343eb8-52d8-4070-831c-12f2111a822c",
    "tenant_id": "default",
    "agent_id": "0f419f95-7b18-45c9-a453-87a5b157010e",
    "client_id": "sp-a1b2c3d4e5f6",
    "description": "Production credentials for GitHub agent",
    "status": "active",
    "created_at": "2026-05-27T19:30:00.000000",
    "client_secret": "sec_rawsecretvalue..."
  }
  ```

> [!IMPORTANT]
> The `client_secret` is returned **only once** upon creation. Subsequent requests to fetch the Service Principal metadata (via `GET /admin/agents/{id}/service-principal`) will omit the secret.

## Authentication and Verification

When the agent attempts to authenticate using its Service Principal client credentials, the system compares the incoming secret against a PBKDF2 hash stored in the database.

## Secret Rotation

To rotate the credentials:
- **Endpoint**: `POST /admin/agents/{id}/service-principal/rotate` (Or via admin logic/recreation)

## Auditing

Every IAM action (service principal creation, token exchanges, access approvals, and access denials) is logged immediately.

- **Endpoint**: `GET /admin/agents/iam/audit`
- **Response Format**:
  ```json
  [
    {
      "id": "78a8...",
      "tenant_id": "default",
      "agent_id": "0f419f95...",
      "event_type": "service_principal_created",
      "actor_id": "admin",
      "actor_type": "user",
      "details": {
        "client_id": "sp-a1b2c3d4e5f6"
      },
      "created_at": "2026-05-27T19:30:00Z"
    }
  ]
  ```

All raw secrets are automatically redacted from audit logs and outputs.

## Operational Guide (Production Ready)

### Activate
Ensure `AGENT_IAM_ENABLED=true`.

### Monitor
Audit logs available at `/admin/agents/iam/audit`.

### Troubleshoot
Verify service principal status via `/admin/agents/{id}/service-principal`.

### Rollback
Revoke service principals or disable the IAM flag.
