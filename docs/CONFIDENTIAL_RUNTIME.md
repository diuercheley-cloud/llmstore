---
owner: platform-ops
status: consolidated
---

# Confidential Inference Runtime

## Overview
The Confidential Inference Runtime provides operational controls and hooks to ensure data privacy during LLM inference. It enforces policies such as prohibited plaintext logging, mandatory input encryption, and immediate memory hygiene (retention).

## Configuration
- `COMMERCIAL_CONFIDENTIAL_RUNTIME_ENABLED`: Enable the confidential runtime module.
- `COMMERCIAL_CONFIDENTIAL_RUNTIME_MODE`:
  - `report_only`: Log violations but do not block requests.
  - `enforce`: Block requests that violate confidentiality policies.
- `COMMERCIAL_CONFIDENTIAL_PROHIBIT_PLAINTEXT_LOGGING`: Global toggle to force hash-only logging of prompts/responses.
- `COMMERCIAL_CONFIDENTIAL_DEFAULT_RETENTION_SECONDS`: Default duration to keep inference data in memory/buffer.

## Confidential Profiles
Profiles define the security posture for a specific client or the entire cluster:
- **Require Encrypted Input**: Blocks any request that does not provide an `encrypted_input` payload.
- **Prohibit Prompt/Response Logging**: Ensures that full text is never written to persistent logs (only cryptographic hashes).
- **Require Model Trust**: Checks if the model being used is from a trusted supply chain.
- **Max Retention**: Defines how long data can persist after the session completes.

## Confidential Sessions
Every request processed under a confidential profile creates a `CommercialConfidentialInferenceSession`. This session tracks:
- Input/Output modes (Plaintext vs. Encrypted).
- Attestation status.
- Applied retention policies.

## Integration Hooks
- **Logging Enforcement**: `enforce_no_plaintext_logging` replaces sensitive content with SHA-256 hashes before logging.
- **Validation**: `validate_confidential_request` runs before inference to check for mandatory encryption.
- **Retention**: `apply_retention_policy` triggers cleanup activities immediately after response generation.

## Note on TEE
This module provides *software-level* operational confidentiality. It is designed as a preparatory layer for formal Trusted Execution Environments (TEE) like Intel SGX or AMD SEV.
