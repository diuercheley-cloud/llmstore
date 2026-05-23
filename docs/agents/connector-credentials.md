# SaaS Connector Credentials

Beyond OAuth, the platform supports various credential types for SaaS connectors.

## Grant Types

- `oauth2`: Managed OAuth tokens with automatic refresh.
- `personal_access_token`: Manually provided tokens for simpler integrations or development.

## Token Rotation

For OAuth tokens, the `TokenRotationService` handles automatic refresh when a token is close to expiry (TTL check).

## Audit Logging

Every credential-related action (registration, rotation, revocation, usage) is recorded in the platform's audit trail.

- `connector_credential_grants`: Tracks which credentials are active for each connector and tenant.
