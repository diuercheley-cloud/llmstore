---
owner: platform-ops
status: consolidated
---

# Sandbox Runtime

The Sandbox Runtime is the underlying execution engine that isolates generated code from the host system.

## Isolation Mechanisms
- **Process Isolation**: Every execution runs in a separate `multiprocessing.Process`.
- **AST Validation**: Code is scanned before execution for forbidden imports and function calls.
- **Global Restriction**: The execution environment only provides access to a safe subset of Python's built-ins.
- **Network/Write Control**: Network and File System access can be toggled via settings (`agent_code_sandbox_network_enabled`, `agent_code_sandbox_write_enabled`).

## Security Policies
- **Timeouts**: Default 5-second timeout to prevent DoS.
- **Blocking**: Access to sensitive files like `/etc/passwd` or `.env` is blocked by AST analysis and restricted built-ins.
