# Sandbox GA Hardening

## Overview
This document outlines the security controls, validation processes, and configuration constraints enforced to mark the Code Sandbox capability as Production-Ready (GA).

## Security Controls
1. **MicroVM Requirement**: In production, execution must run within a hardened sandbox (e.g. gVisor, Firecracker). Using mock or Docker without strict confinement will trigger policy violations unless explicitly configured.
2. **Attestation Requirement**: Every sandbox execution produces a verifiable attestation signature in production.
3. **No Simulated Success**: Fallbacks where the microVM engine is absent but the mock provider pretends to be successful are entirely blocked.
4. **Network and File System Restriction**:
   - `urllib`, `requests`, and `socket` are strictly blocked at code level.
   - Access to paths such as `.env` and `/var/run/docker.sock` is audited and actively blocked by SandboxPolicyEngine.
5. **Execution Limits**: Hard limitations are present on memory, cpu, and output log sizes. Any process exceeding limitations will be terminated or its output truncated gracefully and marked explicitly.

## Tests
Use `make sandbox-ga-test` to validate these compliance rules.
