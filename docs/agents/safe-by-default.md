# Safe-by-Default Posture

The `llm-inference-stack` is built with a **safe-by-default** security philosophy. Every feature in the agentic expansion is disabled by default (opt-in), requires strict authorization boundaries, and undergoes automated policy validation before execution.

## 1. Opt-In Feature Flags
All new capabilities are gated by boolean flags that default to `false`. Examples include:
- `AGENT_CODE_INTERPRETER_ENABLED=false`
- `AGENT_MCP_ENABLED=false`
- `AGENT_KNOWLEDGE_GRAPH_ENABLED=false`
- `AGENT_AUTO_OPTIMIZATION_ENABLED=false`
- `AGENT_OTEL_TRACING_ENABLED=false`

Operators must explicitly set these flags to `true` in their environment configurations to expose these features to tenants.

## 2. Default Sandbox Containment
- Code execution is entirely disabled unless an explicit provider is selected.
- If code interpreter is enabled, the default sandbox provider is set to `mock`, which logs the execution intent without running arbitrary commands.
- Docker and WASM container boundaries do not expose network access or local directories (`.env`, `/var/run/docker.sock`, data directories) by default.

## 3. Human-in-the-Loop Safeguards
- Any action flagged with a high risk level (e.g. database writes, deployment changes, external network calls) triggers a state machine block waiting for user approval in the Approvals Portal.
- Agent optimization results (prompts or policies) are strictly advisory. Candidates cannot be auto-applied or auto-promoted to production without explicit developer and manager approval.

## 4. Leakage Prevention
- Spans and logs are automatically sanitized via a `trace_sanitizer` to remove credentials, bearer tokens, or PII.
- Raw context retrieved via GraphRAG or vector memory is filtered to redact secret-like content prior to being sent back to the client or saved to logs.
