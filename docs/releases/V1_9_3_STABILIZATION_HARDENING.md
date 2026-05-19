# Release Notes: v1.9.3-stabilization-hardening

## Overview
This release focuses on platform stability, observability, and architecture consolidation. It introduces a standardized layer for Service Level Objectives (SLOs), automated readiness checks, and a comprehensive resilience testing framework.

## Key Features

### 1. Standardized Observability
Introduces the `llm_*` metric namespace for Prometheus, covering:
- End-to-end latency and error rates.
- Provider and model health scores.
- Queue wait times and saturation.
- Security (RBAC) and hardware integrity (Attestation) events.

New endpoints:
- `/admin/observability/slo`: Real-time SLO performance report.
- `/admin/observability/platform-health`: Aggregated health status.

### 2. Operational Readiness Pack
The `make operational-readiness` command automates the validation of new deployments, ensuring that infrastructure (DB, Redis), APIs, and security configurations are correctly set up before exposing the platform to users.

### 3. Resilience Testing (Smoke & Chaos)
New test suites to validate system behavior under stress and failure:
- **Smoke Tests**: Verify core flows using mocked dependencies.
- **Chaos Tests**: Simulate timeouts, queue saturation, and attestation failures to verify fallback mechanisms.

### 4. Architecture Simplification
Implementation of a formal deprecation policy. Legacy endpoints now return `X-Deprecated-Endpoint: true`, providing a clear path for technical debt reduction without breaking compatibility.

## Secure Defaults
- `RBAC_ADMIN_ENABLED=false`: Full backward compatibility.
- `PKI_ENABLED=false`: Offline-first by default.
- `ATTESTATION_MODE=advisory`: Non-blocking integrity checks.
- `TOKENIZER_MODE=auto`: Safe fallback to estimation.

## Release Checklist
- [ ] `make test`: All unit and integration tests passing.
- [ ] `make test-smoke-resilience`: Basic platform flows verified.
- [ ] `make test-chaos-resilience`: Fault tolerance verified.
- [ ] `make operational-readiness`: Deployment sanity check.
- [ ] `alembic current`: Database migrations up to date.
- [ ] `bash scripts/check-secrets.sh --all`: No credentials leaked.
