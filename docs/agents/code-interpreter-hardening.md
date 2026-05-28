# Code Interpreter Hardening

The Code Interpreter now enforces a stronger sandbox contract for dynamic execution.

## Defaults

```bash
AGENT_SANDBOX_PROVIDER=docker
AGENT_SANDBOX_FIRECRACKER_ENABLED=false
AGENT_SANDBOX_GVISOR_ENABLED=false
AGENT_SANDBOX_MICROVM_REQUIRED=false
```

Docker remains the default provider. Firecracker and gVisor are opt-in only.

## Hardening Controls

- Static AST policy blocks `subprocess`, `socket`, `os`, `requests`, `open`, `eval`, `exec`, and related escape primitives.
- Network is blocked by default.
- Metadata endpoints are blocked by policy and blackholed at runtime.
- Sensitive mounts, `docker.sock`, and sensitive `/proc` paths are blocked.
- Docker and gVisor runs use read-only rootfs, dropped capabilities, `no-new-privileges`, bounded memory, PID limits, and tmpfs-only writable scratch space.

## Mandatory Sandbox Attestation

Every execution must emit attestation data containing:

- provider
- kernel isolation level
- network mode
- filesystem mode
- limits
- artifact hashes

Execution fails if the provider does not report enough isolation metadata to build valid attestation. In production, this blocks the run entirely.

## Requiring Strong Isolation

To require MicroVM or gVisor isolation:

```bash
AGENT_SANDBOX_MICROVM_REQUIRED=true
AGENT_SANDBOX_PROVIDER=firecracker
AGENT_SANDBOX_FIRECRACKER_ENABLED=true
```

or

```bash
AGENT_SANDBOX_MICROVM_REQUIRED=true
AGENT_SANDBOX_PROVIDER=gvisor
AGENT_SANDBOX_GVISOR_ENABLED=true
```

With `AGENT_SANDBOX_MICROVM_REQUIRED=true`, Docker fallback is blocked.

## Readiness

The readiness report includes:

- sandbox provider available
- provider configured
- provider healthy
- fallback allowed or blocked
