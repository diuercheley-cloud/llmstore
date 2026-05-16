# Formal Plugin ABI & Extension Runtime

## Overview
The plugin runtime provides deterministic records for plugin ABI contracts and extension operations. It is an administrative runtime, not an execution engine.

## ABI Contracts
`PluginABIContract` stores tenant-scoped plugin identity, ABI version, schema version, scope, status, deterministic version, contract hash, and immutable hash.

## Capability Boundaries
`PluginCapabilityBoundary` enforces deny-first boundaries. Restricted capabilities include shell, subprocess, network, dynamic import, external filesystem write, plaintext secret access, kubernetes apply, nomad run, proxmox mutate, and placeholder hardware trust flows only.

## Runtime Compatibility Enforcement
`PluginRuntimeCompatibilityEnforcer` checks contract status, schema compatibility, and semantic version policy. `warning` requires review before activation. `incompatible`, `blocked`, and `revoked` prevent load planning.

## Deterministic Extension Loading
`DeterministicExtensionLoader` creates dry-run load plans only. Ordering is deterministic by `plugin_name`, `plugin_version`, and `abi_version`. There is no real plugin execution and no external dynamic import.

## Isolation Policies
`PluginIsolationPolicyService` applies offline-first defaults:
- deny network
- deny subprocess
- deny dynamic import
- deny external filesystem write
- deny plaintext secret access

## Lifecycle Management
Lifecycle events are audit-friendly. `placeholder_certified` is explicit placeholder certification only. `revoked` and `blocked` require a reason.

## Replay Verification
Replay verification recomputes deterministic hashes for contracts, load plans, and capability boundaries without executing code.

## Federation Compatibility
Federation compatibility is conceptually aligned with Phase 77 federation synchronization. It requires replay-safe contracts and uses placeholder trust only.

## Receipts
Receipts contain:
- `receipt_type`
- `client_id`
- `subject_id`
- `immutable_hash`
- `payload_hash`
- `deterministic_version`
- `signature_placeholder`
- `generated_at`

## Audit Events
Audit events are sanitized, offline-compatible, deterministic, and do not expose sensitive plaintext payloads.

## API Admin
Administrative endpoints support contract creation, listing, detail, capability evaluation, compatibility checks, deterministic load planning, lifecycle recording, replay verification, federation compatibility checks, receipts, and summary retrieval.

## Dashboard
Admin and portal surfaces expose section markers and status cards for the phase, including notices for no real plugin execution, placeholder certification only, and deterministic load simulation only.

## Offline Compatibility
The implementation is offline-first, uses deterministic SHA-256 hashing, avoids random identifiers in the logical path, and does not require SaaS or cloud services.

## Limitations
- no real plugin execution
- no real certification
- no real signature validation
- no external dynamic import
- no third-party code loading
