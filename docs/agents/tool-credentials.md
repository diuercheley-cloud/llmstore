---
owner: platform-ops
status: consolidated
---

# Delegated Tool Credentials

To invoke authenticated third-party services securely without exposing global admin credentials to agents, the platform implements a Delegated Credentials mechanism.

## Cryptography & Key Management

- **AES-GCM Encryption**: Plaintext credentials are encrypted using AES-GCM prior to storage.
- **Key Derivation**: The master encryption key is derived via SHA-256 from the `COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY` environment setting.
- **Nonce Salting**: Each value gets a unique 12-byte random nonce. Nonce and ciphertext are base64-encoded together.

## Credential Resolving & Grants

An agent tool execution resolves credentials only if `AGENT_TOOL_CREDENTIAL_DELEGATION_ENABLED` is `true`.

1. **Resolution Criteria**: The system queries active `AgentToolCredentialGrant` mappings filtering by `tenant_id`, `agent_tool_id`, and optionally `agent_id`.
2. **Checks**:
   - Expiration: Expired grants or credentials are bypassed.
   - Revocation: Credentials with `revoked=True` are ignored.
3. **Parameter Injection**: Upon successful resolution, the raw secret is decrypted and injected into parameters matching authentication patterns (e.g. `api_key`, `secret`, `password`, `token`, `auth`, `credential`).

## Safety & Masking

- **Response Masking**: Lists of credentials return only the `secret_masked` representation (e.g. `sk-...4a5f` or `api...9231`). Raw values are never returned to clients or UI.
- **Audit Sanitization**: Audit trail logs sanitize details using recursive key matching to redact passwords, api keys, and bearer tokens.
