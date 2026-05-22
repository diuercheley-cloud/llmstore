# Ephemeral Credentials

## Overview
To minimize the risk of credential leakage, the agentic plane uses ephemeral (short-lived) credentials for tool execution.

## Lifecycle
1. **Issuance**: Credentials are issued at the start of a tool call or run step.
2. **Scope**: Each credential is scoped to a specific tool or resource path.
3. **Expiration**: Credentials have a short Time-To-Live (TTL), typically 5-15 minutes.
4. **Revocation**: Credentials can be explicitly revoked if a run is cancelled or fails.

## Storage
Ephemeral credentials are stored in the `agent_ephemeral_credentials` table and are automatically purged after expiration.
