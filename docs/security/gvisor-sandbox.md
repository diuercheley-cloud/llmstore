# gVisor Sandbox Isolation

gVisor provides a user-space kernel that intercepts and handles system calls, providing a strong security boundary between the application and the host kernel.

## Usage
Enabled via `AGENT_CODE_SANDBOX_GVISOR_ENABLED=true`.

## Configuration
The platform uses `docker` with the `runsc` runtime to manage gVisor containers.
- **Runtime**: `runsc`
- **Isolation**: Sentry (user-space kernel)
- **Networking**: Disabled by default.
