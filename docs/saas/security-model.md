# SaaS Security Model

## Authentication
- **Admin Access**: Managed by `ADMIN_TOKEN` or RBAC if enabled.
- **Appliance Communication**: Initial enrollment via one-time token. Subsequent heartbeats are authenticated by the assigned `appliance_id`.
- **MTLS (Recommended)**: For production SaaS deployments, Mutual TLS between appliances and the Control Plane is strongly recommended.

## Authorization
- **RBAC**: Separate roles for Organization Admins, Workspace Admins, and Support staff.
- **Revocation**: Central Control Plane can revoke an appliance's authorization at any time, which immediately stops heartbeat acceptance and marks it as offline.

## Audit Logging
- All administrative actions (creating organizations, workspaces, generating tokens, revoking appliances) are recorded in the central audit log.
- Audit logs are partitioned by `organization_id` to ensure tenants can only see their own administrative history.

## Environment Isolation
- `DEPLOYMENT_MODE=appliance`: Disables all managed endpoints and logic, ensuring complete isolation for on-premise users.
- `DEPLOYMENT_MODE=managed_control_plane`: Enables multi-tenant management features.
