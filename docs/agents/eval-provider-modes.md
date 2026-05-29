# Evaluation Provider Modes

> Owner: agent-platform | Status: Stable

The platform separates evaluation runs into three distinct execution modes controlled by the `AGENT_EVAL_PROVIDER` feature flag. This separation ensures that tests can be run safely during local development or CI pipelines without accidentally making costly production LLM API calls.

## Feature Flags

- `AGENT_EVAL_PROVIDER`: Defines the active provider mode. Supported values: `mock` (default), `gateway`, `real`.
- `AGENT_EVAL_REAL_PROVIDER_ENABLED`: Controls if direct API evaluation runs are allowed. Must be `true` to opt-in to `real` mode.

---

## Provider Types

### 1. MockEvalProvider (`mock`)
- **Use Case:** Local developer testing and continuous integration (CI) pipeline validation.
- **Execution:** Uses `MockLLMProvider` with predefined mock responses, avoiding direct or proxied calls to real LLM providers.
- **Safety:** Automatically marks final answer steps with `mock: true` in step metadata. Mocked runs are blocked from production promotion unless overridden.

### 2. GatewayEvalProvider (`gateway`)
- **Use Case:** Staging and pre-production evaluation.
- **Execution:** Runs the execution loop through the internal `AgentRuntime` using standard models via the internal inference gateway.
- **Cost/Safety:** Requires active gateway authorization and is billed normally based on model usage.

### 3. RealProviderEvalProvider (`real`)
- **Use Case:** Hardened end-to-end evaluations directly hitting external model APIs.
- **Execution:** Runs the standard `AgentRuntime` loop, calling external model provider endpoints directly.
- **Requirements:** Requires setting `AGENT_EVAL_REAL_PROVIDER_ENABLED=true` explicitly.

---

## Promotion Gates Enforcement

When promoting an agent to `active` (production) status, the promotion gate checks the evaluation runs associated with the baseline. 

- **CI/Mock Runs:** Runs using the `mock` provider are blocked from promoting the agent to production (or active status) by default. This is governed by `AGENT_EVAL_ALLOW_MOCK_FOR_PROMOTION=false`.
- **Production Readiness:** Active production agents strictly require evaluation via `gateway` or `real` providers to ensure they are verified against live models.
