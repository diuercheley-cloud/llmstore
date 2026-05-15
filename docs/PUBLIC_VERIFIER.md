# Public Verifier CLI + Offline Verification Tool

## Overview

The **Public Verifier CLI** is a standalone, offline tool designed to verify exported **AI Execution Proofs** without requiring access to the control plane, database, or any external service.

This tool ensures that the cryptographic receipts and Merkle timelines produced by the system remain valid even when analyzed in an isolated environment.

## Key Features

- **Independent Verification**: Recomputes Merkle paths and proof hashes locally.
- **Offline Mode**: Works without network access.
- **Batch Processing**: Validates entire directories of proofs at once.
- **Sanitization Audit**: Confirms no sensitive data (prompts/responses) is present in the proof.
- **Detailed Reporting**: Generates both human-readable terminal output and machine-readable JSON reports.

## Installation

The verifier is designed to be lightweight. It requires Python 3.8+ and minimal dependencies.

```bash
# Navigate to the tool directory
cd tools/public_verifier

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Verify a Single Proof

```bash
python3 -m tools.public_verifier.verifier_cli verify <proof_file.json>
```

**Options:**
- `--export <report.json>`: Saves the detailed verification result to a JSON file.

### 2. Batch Verification

```bash
python3 -m tools.public_verifier.verifier_cli verify-batch <directory_path>
```

### 3. Timeline Validation

The tool can also validate the integrity of a timeline chain by checking the `previous_timeline_root` links between consecutive proofs or timeline exports.

## Verifications Performed

1. **JSON Schema**: Ensures the file matches the expected format.
2. **Proof Hash Consistency**: Detects tampering with any field in the proof bundle.
3. **Merkle Inclusion**: Reconstructs the Merkle path from the leaf to the claimed root.
4. **Timeline Root Match**: Confirms the inclusion proof aligns with the timeline's root.
5. **Sanitization Audit**: Scans for forbidden fields like `prompt` or `response`.
6. **Signature Verification**: (Placeholder) Checks the status of the detached signature from the original receipt.

## Limitations

- **Signature Anchoring**: While the tool verifies the proof's internal consistency, trust in the *root* of the timeline depends on the public key of the signing authority (the Control Plane).
- **Not a Legal Audit**: This tool provides cryptographic proof, but does not substitute for a formal legal or regulatory audit.

## Security Considerations

- **No Remote Execution**: The tool never executes code from the proof payloads.
- **Input Sanitization**: All paths and JSON inputs are handled securely.
- **Deterministic**: Re-verification results should be identical regardless of the machine used.
