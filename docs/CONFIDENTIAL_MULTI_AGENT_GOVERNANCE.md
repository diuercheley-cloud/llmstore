# Confidential Multi-Agent Governance

## Overview
Phase 50 introduces a high-integrity coordination layer for multi-agent AI systems. It ensures that agents operate within strict context boundaries, follow mandatory delegation policies, and execute tools under cryptographic audit.

## Key Components

### 1. Agent Profiles & Capabilities
- **Allowed Tools**: Strict allow-list of tools an agent can invoke.
- **Delegation Rights**: Policy-based control over which agents can hand off tasks to others.
- **Context Isolation**: Memory boundaries ensuring no cross-tenant or cross-session leakage.

### 2. Governance Controls
- **Mandatory Tool Approval**: If enabled, sensitive tools require manual human-in-the-loop approval before execution.
- **Confidential Tooling**: Tool inputs and outputs are processed within the Confidential Runtime, ensuring no plaintext leakage to logs.
- **Execution Proofs**: Every agent step and tool call generates a cryptographic receipt, allowing full replayable orchestration audit.

### 3. Orchestration & Delegation
- **Delegation Policies**: Source/Target mapping of allowed agent interactions.
- **Depth Limits**: Prevents recursive delegation loops and ensures accountability.
- **Audit Graph**: Real-time visualization of agent hand-offs and execution flow.

## Configuration
- `COMMERCIAL_AGENT_GOVERNANCE_ENABLED`: Toggle the module.
- `COMMERCIAL_AGENT_GOVERNANCE_MODE`: `audit_only` (log and allow) or `enforce` (block violations).
- `COMMERCIAL_AGENT_MEMORY_ISOLATION_LEVEL`: `strict` (separate memory pools) or `shared`.

## API Endpoints
- `GET /admin/inference/agents/status`: Module health and metrics.
- `GET /admin/inference/agents/profiles`: Manage agent configurations.
- `GET /admin/inference/agents/executions`: Audit active and past agent runs.
- `POST /admin/inference/agents/tool-executions/{id}/approve`: Manual tool approval.

## Security Boundaries
Agents are isolated at the memory level. Context is cleared between sessions unless a specific "Long-term Memory" policy is applied via the RAG Vault. All inter-agent communication is signed and verified against the Cluster Trust Root.
