---
owner: platform-ops
status: consolidated
---

# Sandbox Providers

Supported providers:

- `mock`: deterministic, no real execution, safe for tests and local validation.
- `docker`: ephemeral container, `--network=none`, read-only root, bounded memory and tmpfs.
- `wasm`: reserved for future WASI execution, disabled by default.
