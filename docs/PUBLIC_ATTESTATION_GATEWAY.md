# Public Attestation Gateway

## Overview
The Public Attestation Gateway provides a read-only, tenant-safe interface for verifying cryptographic evidence (receipts, proofs, timelines, and witness quorums) without exposing sensitive data like prompts, responses, or tenant metadata.

## Configuration
- `COMMERCIAL_PUBLIC_ATTESTATION_GATEWAY_ENABLED`: Toggle the gateway (default: `false`).
- `COMMERCIAL_PUBLIC_ATTESTATION_MODE`:
  - `disabled`: Gateway is offline.
  - `local_only`: Only accessible from cluster-internal network.
  - `authenticated`: Requires a valid API key or session.
  - `public_readonly`: Open to the public internet (read-only).
- `COMMERCIAL_PUBLIC_ATTESTATION_RATE_LIMIT_RPM`: Requests per minute per IP (default: `60`).
- `COMMERCIAL_PUBLIC_ATTESTATION_MAX_PAYLOAD_KB`: Max request size (default: `512`).

## Endpoints

### Public Verification
- `POST /attestation/verify/receipt`: Validate an inference receipt hash.
- `POST /attestation/verify/timeline`: Validate a Merkle timeline root.
- `POST /attestation/verify/witness-quorum`: Check if a timeline has met its witness quorum.
- `GET /attestation/status`: Check gateway health and configuration.

### Admin Monitoring
- `GET /admin/inference/attestation/requests`: List recent attestation requests.
- `GET /admin/inference/attestation/results`: List verification results.
- `GET /admin/inference/attestation/status`: Summary of gateway usage.

## Security Controls
1. **Masked IPs**: All source IPs are stored in a masked format (e.g., `192.168.x.x`).
2. **Data Sanitization**: Verification results are stripped of internal IDs and sensitive metadata.
3. **No Mutations**: The gateway can only write to its own request/result logs; it cannot modify inference state.
4. **Rate Limiting**: Protected against DDoS and enumeration attacks.

## Online Verification CLI
The Public Verifier CLI can now verify proofs against a remote gateway:
```bash
python verifier_cli.py verify-online proof.json --gateway-url http://your-gateway/attestation
```
