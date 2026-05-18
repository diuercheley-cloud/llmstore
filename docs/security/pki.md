# Internal PKI (Public Key Infrastructure)

The LLM Inference Stack includes an internal PKI service to manage cryptographic identities for components and plugins.

## Architecture

- **Local Root CA**: A self-signed Root CA generated on the first run when `PKI_ENABLED=true`.
- **Certificate Inventory**: Certificates are tracked in the database for lifecycle management (rotation, revocation).
- **Storage**: CA keys and certificates are stored in `PKI_STORAGE_PATH` (default: `./data/pki`).

## Configuration

- `PKI_ENABLED`: Set to `true` to enable real PKI.
- `PKI_STORAGE_PATH`: Path to store CA files.
- `PKI_CA_ROTATION_DAYS`: Validity period for the Root CA.
- `PKI_CERT_ROTATION_DAYS`: Validity period for issued certificates.

## Management

### Initializing CA
Use the admin endpoint:
`POST /admin/security/pki/init`

### Revocation
Certificates can be revoked by serial number, which updates the local CRL.
