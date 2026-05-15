# Cryptographic Trust Infrastructure (Phase 62)

## Overview
The Cryptographic Trust Infrastructure provides an enterprise-grade abstraction layer over KMS, HSM, and Vault systems, while maintaining strict compatibility with offline and sovereign mode deployments. It replaces previous cryptographic placeholders with a robust, extensible architecture capable of handling detached signatures, envelope encryption, and automated key rotation without mandating cloud connectivity.

## Architecture

The system is built on a modular provider registry (`CryptoProviderRegistry`), allowing dynamic resolution of the correct cryptographic backend based on the tenant or operation context.

### Core Components
1. **CommercialKMSProvider:** Defines the backend system (Local Keystore, Vault, HSM, Sovereign Offline).
2. **CommercialKeyMaterial:** Represents a logical key, storing its state, alias, and an encrypted reference to the actual material or offline blob. Plaintext key material is never logged or exposed.
3. **CommercialSigningProfile:** Links a key material to specific algorithms (e.g., RSA-2048, ECDSA-P256) for signing and verification tasks.
4. **KMSRuntime:** Orchestrates encryption and decryption operations. It validates provider configuration, key status, and maintains an immutable crypto audit trail.
5. **SigningService:** Specialized service for generating and verifying cryptographic signatures for inference receipts, federated workflows, and model supply chain attestation.
6. **KeyRotationService:** Manages key lifecycles, identifying pending rotations based on `CommercialKeyRotationSchedule` and executing non-disruptive key generation and alias updates.

## Supported Providers
- **Local Keystore:** Basic implementation for dev/test and minimal appliance modes.
- **Vault Placeholder:** Abstraction ready for integration with HashiCorp Vault or similar systems via API.
- **HSM Placeholder:** Abstraction ready for PKCS#11 or network HSM appliances.
- **Sovereign Offline Store:** Designed for air-gapped deployments where keys are provided via encrypted, offline-synced blobs.

## Security & Governance
- **Zero Plaintext Key Logging:** The `CommercialKeyMaterial` model only holds references or encrypted blobs. `KMSRuntime` logs operations, not data.
- **Immutable Audit Trail:** All operations (`encrypt`, `decrypt`, `sign`, `verify`) log their success/failure and context to `CommercialCryptoOperation`.
- **Tenant-Scoped Keys:** Keys can be bound to specific `tenant_id`s, ensuring logical isolation in multi-tenant commercial deployments.

## Integration Points
This infrastructure is backwards compatible and prepares the groundwork for integrating with existing features:
- Phase 36/37: Cryptographic Receipts and Attestation Runtime.
- Phase 38: Model Registry and provenance signing.
- Phase 41: Workflow receipts and determinism validation.
- Phase 58: Hardware Attestation.
- Phase 59: Offline Model Lifecycle.

## Remaining Risks & Explicit Limitations
1. **FIPS/Formal HSM Certification:** This architecture does not currently claim formal FIPS compliance or strict HSM integration. The `HSMPlaceholderProvider` requires a concrete implementation (e.g., PKCS#11 driver) to fulfill hardware-level guarantees.
2. **Key Material Transport:** The exact mechanism for injecting `encrypted_key_blob` into the `CommercialKeyMaterial` for Sovereign Offline scenarios is out of scope for the base abstraction and requires a dedicated offline synchronization tool.
3. **Performance Overhead:** Local abstraction layers and database-backed provider/key resolution introduce latency. Aggressive caching strategies might be needed for high-throughput signing (e.g., per-token receipt generation).

## API Endpoints
Admin endpoints are available under `/admin/crypto/`:
- `GET /providers` - List KMS providers.
- `POST /providers` - Register a new provider.
- `GET /keys` - List key material metadata.
- `POST /keys` - Generate a new key.
- `POST /rotate` - Process pending key rotations.
- `POST /sign` - Sign a payload given a profile ID.
- `POST /verify` - Verify a signature.
- `GET /trust-chain` - View the trust chain hierarchy (Mocked for Dashboard).

## Validation
Validation checks can be run via:
```bash
./scripts/validate-crypto-trust.sh
```
This ensures models, services, compilation, and unit tests are functioning correctly.