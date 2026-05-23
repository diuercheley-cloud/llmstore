# Real Provider Validation

## Overview

The platform supports advanced agentic capabilities (reasoning, workflows, connectors). However, to ensure operational readiness, we must validate these capabilities against real LLM providers, not just in mock mode.

The Real Provider Validation suite is a controlled environment designed to test the platform against OpenAI, Anthropic, OpenRouter, and a local llama.cpp instance.

## Feature Flags
- `AGENT_REAL_PROVIDER_VALIDATION_ENABLED`: Set to `true` to enable real provider execution (defaults to `false`).

## Validations Performed

1. **Structured Output**: Verifies the provider can return data matching a specific JSON schema.
2. **Tool Calling**: Ensures the provider can correctly select and format arguments for available tools.
3. **Retry after malformed JSON**: Tests the platform's ability to prompt the provider to correct invalid JSON outputs.
4. **Context Compression**: Checks if long contexts are appropriately compressed while preserving the core goals.
5. **Multi-step Workflow**: Validates the capability to chain multiple steps together successfully.
6. **Memory Injection**: Ensures past context or memory can be successfully injected into the prompt.
7. **Approval Pause/Resume**: Validates the system's human-in-the-loop pause and resume mechanics.
8. **Multi-agent Delegation**: Tests handing off sub-tasks to other specialized agents.

## Safety Rules
- **No Destructive Tools**: Only read-only or mocked SaaS tools are allowed in this suite.
- **Strict Budgets**: Token limits and spend limits are aggressively capped to prevent runaway costs.
- **Short Timeouts**: Strict API timeout bounds to fail fast on unresponsive providers.
- **Synthetic Dataset**: Uses deterministic synthetic data for evaluation.

## Running the Validation

Execute the shell script:

```bash
./scripts/run-real-provider-validation.sh
```

Results are stored in `artifacts/evals/real-provider-validation.md`.
