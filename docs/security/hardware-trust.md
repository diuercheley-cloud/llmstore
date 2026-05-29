---
owner: platform-ops
status: consolidated
---

# Hardware Trust Provider

The Stack abstracts hardware-based security via a pluggable provider interface.

## Supported Providers

- **Mock (Default)**: For development and CI. Returns simulated "trusted" status.
- **File-based**: Uses a local file to simulate hardware measurements.
- **TPM2 (Experimental)**: Interfaces with a physical TPM 2.0 module if available.

## Interface

The `HardwareTrustProvider` interface requires:
- `get_measurements()`: Retrieve platform configuration registers (PCRs).
- `sign_quote(nonce)`: Cryptographically sign a quote using the hardware key.
- `verify_quote(quote, nonce)`: Verify a quote.

## Configuration

- `HARDWARE_TRUST_ENABLED`: Enable hardware trust checks.
- `HARDWARE_TRUST_PROVIDER`: Select provider (`mock`, `file`, `tpm2`).
