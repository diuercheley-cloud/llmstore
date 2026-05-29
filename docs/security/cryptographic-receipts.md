# Cryptographic Receipts Governance and Verification

The platform guarantees inference integrity using real cryptographic signatures (Ed25519) on all completed model calls and agent executions.

## Posture and Security Properties
- **Cryptographic Signature**: All inference receipts are signed with a persistent Ed25519 key configured on the platform.
- **Tamper-Evidence**: Altering any field of the payload (e.g. prompt, response, previous receipt hash) invalidates the signature and is marked as tampered.
- **Key Rotation and Verification**: Operators can export the public key from the control plane using the `/admin/receipts/public-key` endpoint to verify receipts offline.
- **Verifiable Local Timestamps**: Receipts are tagged with high-resolution timestamps signed as part of the immutable hash.

## Configuration & Feature Flags
- `CRYPTO_RECEIPTS_ENABLED`: Enables or disables the cryptographic receipts module.
- `CRYPTO_RECEIPTS_REQUIRE_SIGNATURE`: Enforces signature generation. If the signing key is missing, operations fail closed.
- `CRYPTO_RECEIPTS_EXTERNAL_TIMESTAMP_ENABLED`: Enables timestamp tokens from external TSAs.

## Verification Endpoints
- **POST `/admin/receipts/{id}/verify`**: Performs full validation of the receipt hash, signature, and chaining.
- **GET `/admin/receipts/public-key`**: Returns the active public key in PEM format alongside its key identifier.
- **GET `/admin/receipts/{id}`**: Returns the details of a specific receipt.
