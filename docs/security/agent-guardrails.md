# Agent Safety Guardrails

Safety guardrails provide critical defense-in-depth for agents, detecting and mitigating risks that external policies might miss.

## Guardrail Types

### 1. Input Guardrails
Applied to user inputs before they reach the agent's reasoning loop.
- **Jailbreak Detection**: Detects adversarial prompts (e.g., "DAN" attacks, instruction overrides).
- **Prompt Injection**: Detects attempts to hijack the agent's execution flow.
- **Secret Detection**: Blocks inputs containing API keys, passwords, or tokens.

### 2. Output Guardrails
Applied to model outputs (reasoning, tool calls) and final responses.
- **PII Redaction**: Automatically identifies and redacts emails, phone numbers, and credit cards.
- **Secret Leak Prevention**: Blocks outputs that inadvertently reveal sensitive credentials.
- **Policy Bypass Detection**: Intercepts model outputs that signal successful jailbreaks.
- **Unsafe Tool Use**: Validates that tool inputs don't contain malicious payloads.

## Decision Engine

The guardrail policy orchestrator makes one of the following decisions for each interaction:

| Decision | Action |
|----------|--------|
| `allow` | Content is passed through unchanged. |
| `redact` | Sensitive info (PII) is replaced with placeholders (e.g., `[EMAIL REDACTED]`). |
| `block` | Execution is failed immediately with a safety violation error. |
| `require_human_review` | Run is paused and sent for manual approval. |

## Observability and Auditing

Every guardrail detection and decision is recorded:
- **`agent_guardrail_events`**: Stores the raw content, detection point, and metadata for violations.
- **`agent_guardrail_decisions`**: Stores the final action taken and the rationale.

## Configuration

Guardrails are active by default for all production-grade agents. Redaction rules and block thresholds can be customized per tenant or agent group.
