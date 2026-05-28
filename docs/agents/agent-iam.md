# Agent IAM Architectural Overview

The Agentic AI Platform secures access to SaaS tools and database connectors by providing each agent with a sovereign identity, service principal, and connector-scoped delegated tokens. This design completely eliminates the need for agents to share or access a user's master API key.

## Feature Flags

All IAM features are disabled by default. Enable them via environment variables:

- `AGENT_IAM_ENABLED=true`
- `AGENT_SERVICE_PRINCIPALS_ENABLED=true`
- `AGENT_DELEGATED_TOKENS_ENABLED=true`
- `AGENT_OAUTH_ON_BEHALF_OF_ENABLED=true`

## Core Concepts

### 1. Agent Service Principal
A tenant-scoped identity credential for the agent, consisting of a generated `client_id` and a salted PBKDF2-hashed `client_secret`. 

### 2. Tenant-scoped Identity Binding
Associates the agent with a sovereign identity provider (such as OIDC, DID, or Internal provider).

### 3. User Delegated Grant
A revocable grant (`AgentTokenGrant`) created by a user that authorizes a specific agent to act on their behalf for a particular connector with specific scopes.

### 4. Expiring Scoped Tokens
Expiring delegated tokens (`AgentDelegatedToken`) issued after token exchange. Each token is strictly restricted by:
- **Tenant** (Strict tenant bounds check)
- **Agent** (Bound to a specific agent definition)
- **Connector** (SaaS tool targeting)
- **Action** (Connector capabilities restriction)
- **TTL** (Expiration timestamp check)

## Governance Rules

1. **No Identity, No Write**: Any agent trying to execute a connector write action must have an active `AgentIdentityBinding`.
2. **Immediate Revocation**: Calling revocation on a grant or token marks it as revoked in the database immediately, blocking all subsequent invocations.
3. **Cross-Tenant Prevention**: Tokens or grants created in Tenant A are strictly prohibited from being exchanged or used in Tenant B.
4. **Production Enforcement**: When production mode is active (`ENV=production` or `FASTAPI_ENV=production`), every agent executing a connector action *must* have an active Service Principal registered.
5. **No Secret Leaks**: Raw secrets (tokens, client secrets) are only returned *once* in creation/exchange responses. They are hashed using SHA-256 or PBKDF2-HMAC before storage in the DB and are always redacted in audit logs.
