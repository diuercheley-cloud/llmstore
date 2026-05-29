# Capability Signing Policy

## Supply Chain Integrity
To ensure the integrity of the agentic ecosystem, all capabilities and bundles must be cryptographically signed.

### Environment Constraints
1. **Production**: Both internal and external packages MUST be signed. Unsigned internal bundles are blocked even if they originate from within the organization.
2. **External/Marketplace**: Mandatory signature verification is enforced in ALL environments. Unsigned third-party code is never executed.
3. **Development/Local**: Internal unsigned packages may be permitted ONLY if `ALLOW_UNSIGNED_INTERNAL_BUNDLES=true` is set. An `[AUDIT WARNING]` will be emitted to the logs.

### Verification Steps
- **Manifest Checksum**: A `sha256` checksum of the binary payload must match the manifest.
- **Signature Validity**: The signature must be resolvable via a registered public key and must cover the payload.
- **Trust Score**: Bundles with valid signatures receive a 1.0 trust score.

Run `make capability-signature-gate` to enforce these gates.
