# Real Provider Validation for Agentic Runtime

## Overview

The Real Provider Validation suite performs controlled end-to-end validation
of LLM providers used by the Agentic AI Platform. It replaces the previous
stub-only validation with real HTTP calls to configured provider endpoints,
while maintaining strict budget, timeout, and data safety guards.

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_REAL_PROVIDER_VALIDATION_ENABLED` | `false` | Master switch for validation |
| `AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID` | `false` | Allow paid provider calls |
| `AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL` | `1.00` | Max spend per suite run |
| `AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS` | `60` | Per-request timeout |

## Supported Providers

| Provider | Cost Tier | Requires API Key | Notes |
|----------|-----------|-----------------|-------|
| `mock` | Free | No | Always available, no network |
| `local_gateway` | Free | No | Local inference proxy |
| `local_llama_cpp` | Free | No | Local llama.cpp server |
| `openrouter` | Paid | `OPENROUTER_API_KEY` | Remote API |
| `openai_compatible_custom` | Paid | `AGENT_CUSTOM_OPENAI_API_KEY` | Custom OpenAI-compatible |

## Validations (8 checks)

1. **basic_model_call** - Simple prompt, checks non-empty response, records
   provider/model/tokens/latency/cost.
2. **structured_output** - Forces JSON schema response, validates parse,
   retries up to 3 times on malformed JSON.
3. **tool_call_format** - Requests a tool call, validates tool_call wire format
   (id, type, function name, JSON arguments). No real side effects.
4. **memory_injection** - Injects synthetic memory via system prompt, verifies
   the model uses the provided context.
5. **context_compression** - Sends 20-message history, validates the model
   preserves the original goal after compression.
6. **fallback** - Simulates primary provider failure, validates fallback
   to an available secondary provider.
7. **budget_guard** - Validates the suite stops when budget is exceeded.
8. **timeout_guard** - Validates timeout handling with explicit error on
   unreachable endpoints.

## Usage

### CLI

```bash
# Dry-run (mock only, no real calls)
make agent-real-provider-validation

# Real mode with all configured providers
make agent-real-provider-validation-real

# Or via script directly
./scripts/run-agent-real-provider-validation.sh --dry-run
./scripts/run-agent-real-provider-validation.sh --real --budget 0.50 --timeout 30
```

### Admin API

```bash
# Run validation suite
curl -X POST http://localhost:8000/admin/agents/provider-validation/run \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# With options
curl -X POST "http://localhost:8000/admin/agents/provider-validation/run?providers=mock,openrouter&allow_paid=false&budget_brl=0.50"

# Get latest results
curl http://localhost:8000/admin/agents/provider-validation/latest \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# List available providers
curl http://localhost:8000/admin/agents/provider-validation/providers \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Check recency
curl http://localhost:8000/admin/agents/provider-validation/check \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Artifacts

Results are written to `artifacts/evals/real-provider-validation/latest/`:

- `summary.md` - Human-readable markdown report
- `results.json` - Machine-readable JSON with all metrics
- `provider-matrix.md` - Feature coverage matrix per provider

## Safety Rules

1. **No destructive tools** - validation never executes shell, DB, or HTTP tools.
2. **Synthetic dataset only** - no real prompts, documents, or PII are used.
3. **API key masking** - keys are masked in logs and artifacts.
4. **Budget enforcement** - suite stops when budget is exceeded.
5. **Timeout enforcement** - each request has a mandatory timeout.
6. **Paid provider guard** - paid providers are skipped unless explicitly allowed.

## Architecture

```
User / CI / Admin API
        |
        v
RealProviderValidator
  |-- _check_enabled()        -- feature flag gate
  |-- _check_paid_allowed()   -- paid provider gate
  |-- _check_configured()     -- endpoint reachability + key presence
  |
  |-- validate_basic_model_call()     -- HTTP POST to /v1/chat/completions
  |-- validate_structured_output()     -- JSON schema enforcement + retry
  |-- validate_tool_call_format()     -- tool call wire format validation
  |-- validate_memory_injection()     -- synthetic memory context test
  |-- validate_context_compression()  -- long context + compression
  |-- validate_fallback()             -- primary failure + fallback
  |-- validate_budget_guard()         -- budget limit enforcement
  |-- validate_timeout_guard()        -- timeout error handling
  |
  v
Artifacts: summary.md, results.json, provider-matrix.md
```

## GA Readiness

GA readiness can verify existence of recent real provider validation via:

```python
from app.services.agents.provider_validation import is_recent_validation_available
is_recent_validation_available(max_age_hours=24)  # True if run within 24h
```

Or via the admin check endpoint:

```bash
curl http://localhost:8000/admin/agents/provider-validation/check
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_LOCAL_GATEWAY_ENDPOINT` | `http://localhost:8080/v1/chat/completions` | Local gateway URL |
| `AGENT_LOCAL_GATEWAY_MODEL` | `local-model` | Model for local gateway |
| `AGENT_LOCAL_LLAMA_CPP_ENDPOINT` | `http://localhost:8080/v1/chat/completions` | llama.cpp server URL |
| `AGENT_LOCAL_LLAMA_CPP_MODEL` | `llama-3.2-1b` | Model for llama.cpp |
| `AGENT_CUSTOM_OPENAI_ENDPOINT` | `` | Custom OpenAI-compatible endpoint |
| `AGENT_CUSTOM_OPENAI_API_KEY` | `` | API key for custom endpoint |
| `AGENT_CUSTOM_OPENAI_MODEL` | `gpt-4o-mini` | Model for custom endpoint |
| `OPENROUTER_API_KEY` | `` | OpenRouter API key |
| `AGENT_OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Model for OpenRouter |
