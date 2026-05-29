---
owner: platform-ops
status: consolidated
---

# LLM Provider Modes

This document describes the strict provider mode separation for the agent LLM provider layer.

## Overview

The agent platform supports three explicit LLM provider modes. Each mode has distinct behavior and deployment constraints. Silent fallback between modes is never allowed.

## Provider Types

| Provider | Enum Value | Description | When to Use |
|----------|-----------|-------------|------------|
| **Mock** | `mock` | Returns pre-configured or default responses. No external LLM calls. | CI, local development, unit tests |
| **Gateway** | `gateway` | Routes through the internal inference gateway pipeline with model policy, routing, quota, and billing. | Pilot, production staging |
| **Real** | `real` | Direct external LLM provider call, bypassing the internal gateway. | Production, GA, high-throughput |

## Deployment Mode Rules

| Deployment Mode | Allowed Providers | Mock Behavior |
|----------------|-------------------|---------------|
| `appliance` / `development` | mock, gateway, real | Allowed (default) |
| `pilot` | gateway, real (mock allowed with warning) | Logs warning at startup |
| `production` | gateway, real (mock blocked by default) | Raises `MockProviderError` |
| `enterprise_managed` | gateway, real (mock blocked by default) | Raises `MockProviderError` |

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_LLM_PROVIDER` | `mock` | Selects provider: `mock`, `gateway`, or `real` |
| `AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION` | `false` | Override to allow mock in production (NOT for GA) |
| `AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION` | `true` | Enforce gateway/real provider in production |

## Provider Response Metadata

Every provider response includes:

| Field | Description |
|-------|-------------|
| `provider_type` | Enum value: `mock`, `gateway`, `real` |
| `model_id` | The resolved model identifier |
| `backend_id` | The inference backend UUID used |
| `execution_mode` | Deployment mode at time of execution |
| `tokens` | `{prompt: N, completion: N}` |
| `latency` | Total latency in milliseconds |
| `fallback_used` | Boolean: whether a route fallback occurred |
| `validation_status` | `mock_bypass`, `validated`, `real_provider`, or error |

## Readiness Checks

The `AgentReadinessService` includes an `llm_provider` check that:

- Reports mock provider usage warnings in pilot mode
- Blocks readiness (status: `BLOCKED`) if mock is active in production without override
- Reports degraded readiness (status: `DEGRADED`) if mock is active with production override

## GA Readiness

The `GAReadinessService` scores `llm_provider_ok` as a GA-critical check:

- **Pass**: gateway or real provider in production mode
- **Fail**: mock provider in production mode (even with override)

## Error Handling

| Condition | Error | Message |
|-----------|-------|---------|
| Mock in production | `MockProviderError` | "Mock LLM provider is not allowed in deployment mode 'production'." |
| Provider unavailable | `ProviderUnavailableError` | "No active backend for agent model" or "All LLM routes failed" |
| Invalid provider value | `ValueError` | "Invalid AGENT_LLM_PROVIDER. Must be one of: mock, gateway, real" |

## Example Configurations

### Local development (default)
```bash
AGENT_LLM_PROVIDER=mock
AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=false
AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION=true
```

### Pilot evaluation
```bash
AGENT_LLM_PROVIDER=gateway
AGENT_REAL_LLM_ENABLED=true
```

### Production
```bash
AGENT_LLM_PROVIDER=gateway
AGENT_REAL_LLM_ENABLED=true
AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=false
AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION=true
```

### GA / Enterprise
```bash
AGENT_LLM_PROVIDER=real
AGENT_REAL_LLM_ENABLED=true
AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=false
AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION=true
```
