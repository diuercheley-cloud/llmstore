# Production Sandbox Policies

The Agentic AI Platform enforces strong isolation for code execution in production environments.

## Sandbox Providers
The following providers are supported for production use:
- **gVisor**: User-space kernel isolation via `runsc`.
- **Firecracker**: MicroVM isolation for near-hardware security.
- **Docker**: Supported only for low-risk environments or development/pilot phases.

## Security Constraints
- **Simulation Blocking**: Simulated sandboxes (Mock/Dry-run) are strictly blocked in production if `AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER=false`.
- **MicroVM Requirement**: If `AGENT_CODE_SANDBOX_MICROVM_REQUIRED=true`, only Firecracker or gVisor are allowed.
- **Attestation**: Every execution generates a cryptographical attestation including provider details, isolation level, and resource limits.

## Network and Filesystem
By default, all production sandboxes are launched with:
- `network=none`
- `read-only-rootfs=true`
- Restricted `/proc` and metadata endpoint access.
