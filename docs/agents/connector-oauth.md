# SaaS Connector OAuth

The Agentic AI Platform provides a secure foundation for managing SaaS credentials using OAuth 2.0.

## Security Architecture

- **Encrypted Storage**: All tokens (access and refresh) and client secrets are encrypted at rest using the `ConnectorSecretStore`.
- **No Raw Token Exposure**: The API and logs never expose raw tokens. Internally, connectors work with credential references.
- **Tenant Isolation**: OAuth clients and tokens are strictly partitioned by `tenant_id`.

## OAuth Flow

1. **Register Client**: Register the SaaS application (e.g., GitHub App) using `POST /admin/agents/connectors/{name}/oauth/clients`.
2. **Start Flow**: Initiate the flow using `POST /admin/agents/connectors/{name}/oauth/start`. This returns an `auth_url`.
3. **Callback**: The external platform redirects to the platform callback, which is then handled by `POST /admin/agents/connectors/{name}/oauth/callback`.

## Governance

- **Feature Flag**: OAuth is controlled by `AGENT_CONNECTOR_OAUTH_ENABLED` (default: false).
- **Scope Policies**: Actions are checked against the scopes associated with the token via the `ConnectorScopeManager`.

## Environment Variables

- `AGENT_CONNECTOR_ENCRYPTION_KEY`: The Fernet key used to encrypt secrets.
