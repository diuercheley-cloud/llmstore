# Standardized Agent Bundle (SAB)

## Overview
The Standardized Agent Bundle (SAB) is a portability format for AI agents, inspired by the OCI (Open Container Initiative) standards. It allows agents, including their instructions, tool schemas, memory policies, and evaluation suites, to be packaged into a single, verifiable manifest for transfer between different platform environments (e.g., dev, staging, production).

## Bundle Structure
An SAB manifest contains:
- **Agent Metadata**: ID, name, version, and instructions.
- **Dependencies**: Integrated tool schemas and cognitive memory policies.
- **Eval Suite**: Automated test cases and success criteria for the agent.
- **Sanitized Memory**: (Optional) A snapshot of relevant cognitive memories, redacted to remove PII and secrets.
- **Integrity**: SHA-256 checksums and cryptographic signatures.
- **Provenance**: Records of origin tenant and export history.

## Governance Rules
1. **Immutable Manifest**: Any tampering with the bundle contents results in a checksum mismatch and import failure.
2. **Mandatory Signing**: In production environments, only bundles signed by trusted keys can be imported.
3. **Safety First**:
   - Import never activates an agent automatically; it creates a `draft` definition.
   - Memory snapshots are scanned for raw secrets during import.
4. **Compatibility**: The importer enforces a platform version check to ensure the agent's logic is compatible with the target runtime.

## Usage

### Exporting an Agent
`POST /admin/agents/sab/export/{agent_id}`
Generates a signed manifest for the specified agent.

### Importing an Agent
`POST /admin/agents/sab/import?tenant_id={target_tenant}`
Validates the manifest and creates a new agent definition in `draft` status.

### Verifying a Bundle
`POST /admin/agents/sab/verify`
Performs integrity and security checks on a manifest without performing an import.
