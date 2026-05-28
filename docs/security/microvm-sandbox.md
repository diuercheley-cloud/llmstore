# MicroVM and gVisor Sandbox

The Code Interpreter sandbox supports multiple isolation providers with Docker as the default runtime and Firecracker or gVisor as opt-in hardened providers.

## Feature Flags

```bash
AGENT_SANDBOX_PROVIDER=docker
AGENT_SANDBOX_FIRECRACKER_ENABLED=false
AGENT_SANDBOX_GVISOR_ENABLED=false
AGENT_SANDBOX_MICROVM_REQUIRED=false
```

## Provider Model

- `docker`: default provider for local, mock, and standard production-compatible deployments.
- `firecracker`: opt-in MicroVM provider. It is blocked unless `AGENT_SANDBOX_FIRECRACKER_ENABLED=true`.
- `gvisor`: opt-in user-space kernel isolation provider. It is blocked unless `AGENT_SANDBOX_GVISOR_ENABLED=true`.
- `mock`: deterministic provider for tests. It still emits sandbox attestation so the execution contract remains uniform.

## Enforcement

- Network is disabled by default with `--network=none`.
- Metadata endpoints are blackholed.
- Sensitive mounts are denied by policy.
- `docker.sock` access is denied by policy and never mounted.
- Sensitive `/proc` paths are denied by policy.
- Every execution emits sandbox attestation with provider, kernel isolation, network mode, filesystem mode, limits, and artifact hashes.

## Production Posture

Set the following to require strong isolation:

```bash
AGENT_SANDBOX_MICROVM_REQUIRED=true
AGENT_SANDBOX_PROVIDER=firecracker
```

or

```bash
AGENT_SANDBOX_MICROVM_REQUIRED=true
AGENT_SANDBOX_PROVIDER=gvisor
```

When `AGENT_SANDBOX_MICROVM_REQUIRED=true`, Docker is rejected and fallback is blocked.
