---
owner: platform-ops
status: consolidated
---

# Tenant Encryption Controls & Confidential Computing (Phase 36)

## Overview
Phase 36 introduces enterprise-grade cryptographic isolation for multi-tenant environments. It provides tenant-scoped encryption keys, envelope encryption for artifacts, and confidential export controls to ensure that sensitive data is protected at rest and during transit (federation).

## Core Components

### 1. Tenant-Scoped Encryption Keys (DEKs)
Each tenant (Client) has its own set of Data Encryption Keys (DEKs) managed by the `TenantEncryptionService`.
- **Envelope Encryption**: DEKs are generated locally and wrapped (encrypted) using a Master Key defined in the system configuration (`COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY`).
- **Key Purpose**: Keys are scoped by purpose (e.g., `policy`, `evidence`, `audit`, `billing`, `export`).
- **Key Lifecycle**: Supports `active`, `rotating`, `deprecated`, and `revoked` statuses.

### 2. Envelope Encryption for Artifacts
Sensitive artifacts such as policy bundles and evidence packages are encrypted before storage.
- **Algorithm**: AES-256-GCM (Authenticated Encryption with Associated Data).
- **Storage**: The `CommercialEncryptedArtifact` model stores the encrypted payload, a hash for integrity verification, and a reference to the key used.

### 3. Secret Classification
Data is automatically classified into four levels:
- **Public**: Non-sensitive data.
- **Internal**: Default classification for system data.
- **Confidential**: Data containing PII (emails, names) or prompts/responses.
- **Restricted**: Highly sensitive data like API keys, passwords, and private keys.

### 4. Confidential Export Controls
Controls the visibility of sensitive data during exports (CSV/JSON/Reports):
- **Block Restricted**: By default, `restricted` data is blocked from exports (`[BLOCK: RESTRICTED]`).
- **Redact Restricted**: Optional mode to redact instead of block (`[REDACTED: RESTRICTED]`).
- **Encrypt Confidential**: Optional mode to encrypt `confidential` fields in exports.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `COMMERCIAL_TENANT_ENCRYPTION_ENABLED` | `true` | Enable/disable the encryption service. |
| `COMMERCIAL_TENANT_ENCRYPTION_MODE` | `report_only` | `disabled`, `report_only`, or `enforce`. |
| `COMMERCIAL_TENANT_ENCRYPTION_BLOCK_RESTRICTED_EXPORTS` | `true` | Block restricted fields in exports. |
| `COMMERCIAL_TENANT_ENCRYPTION_AUTO_ROTATION_DAYS` | `90` | Days until a key is marked for rotation. |
| `COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY` | - | 32-character string used to wrap tenant keys. |

## Administrative API

- `GET /admin/security/encryption/keys`: List tenant keys.
- `POST /admin/security/encryption/keys`: Create a new tenant key.
- `POST /admin/security/encryption/keys/{id}/rotate`: Rotate a key.
- `POST /admin/security/encryption/keys/{id}/revoke`: Revoke a key (prevents decryption).
- `POST /admin/security/encryption/encrypt`: Manual encryption of a payload.
- `POST /admin/security/encryption/decrypt`: Manual decryption (audit logged).
- `GET /admin/security/encryption/audit`: View encryption audit trail.

## Limitations
- Does not currently require an external KMS (Hardware Security Module), though it is designed to be compatible with one.
- Does not provide formal Confidential Computing (e.g., Intel SGX / AMD SEV) but implements the software-level cryptographic equivalent for tenant isolation.
