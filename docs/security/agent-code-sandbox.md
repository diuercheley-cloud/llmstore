---
owner: platform-ops
status: consolidated
---

# Agent Code Sandbox

The sandbox posture is opt-in and offline-first.

- `mock` is the default provider for CI, tests, and appliance mode.
- `docker` is available only when `AGENT_CODE_SANDBOX_DOCKER_ENABLED=true`.
- `wasm` is registered but remains experimental and disabled by default.

Default controls:

- Network disabled
- Writes disabled
- Protected filesystem paths denied
- Output truncated to bounded limits
- Secret-like artifacts rejected before storage
