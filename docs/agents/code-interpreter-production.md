# Code Interpreter Production Guide

The Code Interpreter has graduated to production-grade GA with stringent guarantees to support robust multi-tenant environments.

## Features
- **Deterministic Attestations**: Output is bound to the exact input and provider.
- **Provider Parity**: Built-in validation of `gvisor` or `firecracker` providers to avoid simulated successful bypasses.
- **Strict Isolation**: Blocked imports, zero network connectivity (unless strictly scoped via agent capabilities with explicit human approval for high-risk operations), and restrictive filesystem profiles.
- **Audit Trails**: Full records of `SandboxPolicyDecision` and truncated outputs.

## Deployment Requirements
Ensure that your cluster implements `runsc` binaries or equivalent for the chosen microVM deployment.
Enable `AGENT_SANDBOX_PRODUCTION_REQUIRES_ATTESTATION=true` to guarantee environment compliance.
