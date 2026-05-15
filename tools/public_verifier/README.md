
# Public Verifier CLI

Standalone tool for offline verification of AI Execution Proofs.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Verify a single proof
```bash
python -m tools.public_verifier.verifier_cli verify proof.json
```

### Verify a single proof and export report
```bash
python -m tools.public_verifier.verifier_cli verify proof.json --export report.json
```

### Batch verification
```bash
python -m tools.public_verifier.verifier_cli verify-batch ./proofs/
```

## Verifications performed
- JSON Schema validity
- Proof Hash consistency (tamper detection)
- Merkle Inclusion Proof (path validation)
- Timeline Root match
- Sanitization (no prompt/response leakage)
- Receipt Signature status
