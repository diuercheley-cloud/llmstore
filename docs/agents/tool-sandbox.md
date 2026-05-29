---
owner: platform-ops
status: consolidated
---

# Tool Sandbox Execution

The execution sandbox ensures all agent tools execute inside a controlled, isolated runtime boundary with strict limits on resources, execution duration, and output volume.

## Sandbox Types

- **Mock (Default)**: Simulates tool execution and registers execution records without making real calls. Useful for testing and dry-run assertions.
- **Local**: Executes execution steps programmatically with strict allowlists and timeouts.
- **Docker**: Future extension for full operating system level container isolation.

## Runtime Constraints

1. **Timeout Enforcement**: Every tool must specify `timeout_seconds`. If execution exceeds this window, the sandbox raises a timeout exception and updates the database state to `"timeout"`.
2. **Command Allowlist**: If a tool defines `allowed_commands`, parameters specifying a command (such as `"command"`, `"cmd"`, or `"operation"`) are validated. Only allowlisted commands are allowed execution.
3. **Output Volume Limit**: Results are serialized to JSON. If the output exceeds `output_limit_bytes` (defaulting to 50KB), the output log is truncated, and the status is modified to `"truncated"`. This prevents agent memory flooding and DoS attacks.
4. **Shell Commands Isolation**: Shell commands are disabled by default. If `tool_category` is `"shell_command"`, execution is blocked unless `AGENT_DESTRUCTIVE_TOOLS_ENABLED` feature flag is active.
