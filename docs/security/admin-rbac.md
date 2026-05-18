# Admin RBAC

`RBAC_ADMIN_ENABLED=false` preserves the legacy administrative flow based on `X-Admin-Token`. In this mode, the existing token-based behavior remains active and no administrative user lookup is required.

`RBAC_ADMIN_ENABLED=true` switches admin APIs to real RBAC enforcement. The same `X-Admin-Token` header is still used, but the token must belong to an active record in `admin_users` and the request must satisfy the permission required by the target endpoint.

## Data Model

- `admin_users`: administrative principals authenticated by token hash.
- `admin_roles`: named administrative roles.
- `admin_permissions`: granular permission catalog.
- `admin_user_roles`: user-to-role assignments.
- `admin_role_permissions`: role-to-permission assignments.
- `admin_audit_events`: immutable audit trail for authn/authz and RBAC mutations.

## Seeded Permissions

- `clients:read`, `clients:write`, `clients:delete`
- `billing:read`, `billing:write`
- `providers:read`, `providers:write`
- `models:read`, `models:write`
- `rag:read`, `rag:write`, `rag:delete`
- `tts:read`, `tts:write`
- `security:read`, `security:write`
- `governance:read`, `governance:write`
- `system:read`, `system:write`
- `superadmin:all`

## Seeded Roles

- `superadmin`
- `admin`
- `operator`
- `billing_manager`
- `security_auditor`
- `read_only`

## Bootstrap and Migration

The seed is idempotent and creates a legacy bootstrap admin user backed by the current `ADMIN_TOKEN`. This preserves progressive migration:

1. Keep `RBAC_ADMIN_ENABLED=false` while preparing users and roles.
2. Use the RBAC endpoints with the bootstrap token to create real admin users.
3. Enable `RBAC_ADMIN_ENABLED=true`.
4. Rotate away from the bootstrap token when the environment is fully migrated.

## Enforcement

When RBAC is enabled, existing admin endpoints are mapped to domain permissions from the request path and HTTP method. Read requests require `*:read`. Mutating requests require `*:write`, and delete operations use `*:delete` where defined.

The dedicated RBAC management endpoints live under `/admin/rbac/*` and require `superadmin:all`.

## Audit Events

`admin_audit_events` stores:

- successful and failed admin authentication
- permission denials
- admin user creation, update and deletion
- role assignment changes
- permission and role updates
