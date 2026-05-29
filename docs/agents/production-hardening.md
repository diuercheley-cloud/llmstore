---
owner: platform-ops
status: consolidated
---

# Agent Platform Production Hardening Guide

Operating autonomous agents in production requires mitigating risks related to privilege escalation, data leakage, and denial of service. Follow these policies to harden your stack:

## 1. Code Interpreter Hardening
- **Disable Local/Mock execution in Production**: Never use `mock` sandbox provider for untrusted tenant code. Always run code inside containers.
- **Provider Settings**: Set `AGENT_CODE_SANDBOX_PROVIDER=docker`.
- **Resource Limits**: Always set strict CPU shares, memory limits, and process time-limits to prevent resource exhaustion attacks.
- **No Shared Sockets**: Do not mount `/var/run/docker.sock` inside execution runtimes.
- **Read-Only Root**: Configure containers with read-only root filesystems where possible, writeable only to temporary directories (`/tmp`).

## 2. Model Context Protocol (MCP) Security
- **Strict Allowlist**: Ensure `AGENT_MCP_SAMPLING_ENABLED=false` by default. Do not allow agents to run arbitrary tool prompts or sample models without operator permission.
- **Attestation**: Enable tool capability validation. Require administrators to approve each tool discovered on external MCP servers before exposing it to agents.
- **Network Boundaries**: Keep `AGENT_MCP_EXTERNAL_NETWORK_ENABLED=false` unless specific server integrations are approved.

## 3. Advanced Memory & Context Redaction
- **PBP / Secret Filtering**: Ensure the memory summarizer and GraphRAG retrieval redact API keys, tokens, and secret patterns (`sk-...`, etc.) before persistence.
- **Consent and Expiration**: Configure memory retention limits to auto-delete working memory sessions after completion.

## 4. Human-in-the-Loop Approvals
- **High-Risk Action Gates**: Configure policy rules (e.g. `tool_policy.py`) to trigger mandatory manual reviews for destructive operations, external network calls, and actions exceeding budget ceilings.
