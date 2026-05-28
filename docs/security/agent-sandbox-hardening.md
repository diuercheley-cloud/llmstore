# Agent Sandbox Hardening

The Agent Execution Plane implements multi-layered security to prevent sandbox escapes and unauthorized resource access during tool execution.

## Defense-in-Depth Layers

### Layer 1: Static Analysis
Before any tool is executed, the `SandboxEscapeAnalyzer` performs a static scan of the input parameters and any code snippets (e.g., Python, Bash).

- **Path Blocking:** Explicitly blocks access to sensitive files like `.env`, `id_rsa`, and system directories like `/proc`.
- **IP Blocking:** Blocks access to local services and cloud metadata services (169.254.169.254).
- **Code Linting:** Prevents use of dangerous modules (`os`, `subprocess`, `socket`) in interpreter tools.

### Layer 2: Runtime Sandbox
Execution is wrapped in `execute_in_sandbox`, which enforces:
- **Timeouts:** Total execution time is capped.
- **Output Limits:** Prevents memory exhaustion by truncating large results.
- **Command Allowlisting:** Only authorized commands can be executed in shell-like tools.
- **Explicit execution mode:** `mock` and `dry_run` may emit simulated output, but `real` mode without a concrete callable fails closed instead of returning placeholder success.

### Layer 3: Governance Policies
The `AgentPolicyEngine` and human approval workflows ensure that even "safe-looking" tool calls are aligned with the agent's purpose and the user's intent.

## Verification
You can run the sandbox security suite using:

```bash
make agent-sandbox-security
```

Results are documented in `artifacts/security/agent-sandbox-security.md`.
