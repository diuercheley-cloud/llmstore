# Phase 74: Signed Adapter Registry

## Overview
Phase 74 implements a deterministic and offline-first registry for adapter manifests from the Controlled Adapter Sandbox (Phase 73). This registry provides governance, versioning, and status management for adapters without requiring real-time external connectivity or real cryptographic signatures (using placeholders instead).

## Goals
- Provide a central, deterministic registry for adapter manifests.
- Implement a lifecycle for registry entries: `draft`, `submitted`, `approved`, `rejected`, `revoked`, `blocked`, `deprecated`.
- Enforce registry policies (e.g., sandbox requirement, dry-run defaults).
- Maintain deterministic hashes for registry entries and manifests.
- Provide allowlist and blocklist management with precedence rules.
- Generate verifiable (placeholder) receipts for registry actions.

## Components

### 1. Registry Models
- `SignedAdapterRegistryEntry`: The core registry entry linking to an `AdapterManifest`.
- `AdapterRegistryPolicy`: Tenant-scoped policies for registry compliance.
- `AdapterRegistryDecision`: Audit log of status transitions.
- `AdapterRegistryReceipt`: Action receipts with placeholder signatures.
- `AdapterRegistryBlocklistEntry` / `AdapterRegistryAllowlistEntry`: Deterministic lists for manifest hashes.

### 2. Services
- `SignedAdapterRegistryService`: Manages transitions and lifecycle.
- `AdapterRegistryPolicyEngine`: Validates manifests and entries against policies.
- `AdapterRegistryListService`: Manages allowlists and blocklists.
- `AdapterRegistryReceipts`: Generates action receipts.

### 3. API
- `POST /admin/operations/adapter-registry/entries`: Register a new manifest.
- `POST /admin/operations/adapter-registry/entries/{id}/approve`: Approve an entry.
- `POST /admin/operations/adapter-registry/entries/{id}/block`: Block an entry and add to blocklist.
- `POST /admin/operations/adapter-registry/policies`: Create a new registry policy.

## Security & Safety Constraints
- **Signature Placeholders:** No real PKI or cryptographic signatures are used. All signatures are deterministic placeholders.
- **No Execution:** This phase does NOT implement adapter execution. It only manages the registry.
- **Offline-First:** All hashing and validation are performed locally and deterministically.
- **Precedence:** The blocklist always takes precedence over the allowlist and approval status.

## Deterministic Hashing
All registry hashes (`registry_hash`, `manifest_hash`, `immutable_hash`) are computed using SHA-256 with canonical JSON representation of payloads. Timestamps are excluded from logical hashes to maintain determinism across different environments.
