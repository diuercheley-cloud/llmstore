# LLM Harness Production Core Promotion Path

This document defines the formal promotion path and objective acceptance criteria for the modular LLM Harness to achieve **Production Core** status.

## Promotion Levels

Promotion of the LLM Harness proceeds through four distinct levels of maturity:

1. **Experimental**
   - **Scope**: Local prototyping, initial development.
   - **Characteristics**: Stub providers permitted, minimal validation, manual execution.
   - **Gate**: None.

2. **Validated**
   - **Scope**: Integrated local automation, developer-ready.
   - **Characteristics**: Passing unit tests, syntax validation, and local CLI tests.
   - **Gate**: Successful execution of `scripts/validators/validate-llm-harness.sh`.

3. **Production Candidate**
   - **Scope**: Feature-flagged staging and pilot production runs.
   - **Characteristics**: Real provider clients configured, mock integration tests, basic safety policy checks.
   - **Gate**: Active integration with Control Plane services, feature flag gate.

4. **Production Core**
   - **Scope**: Default-enabled, mandatory runtime module for all agentic workflows.
   - **Characteristics**: Zero network bypass, real AgentClient execution, strict sandboxing with guaranteed Docker cleanup, no hardcoded paths or short-circuit logic.
    - **Gate**: Formal promotion check (`make production-core-check-llm-harness` executing `scripts/validators/check-llm-harness-production-core.py`) validating all core criteria.

---

## Production Core Requirements

To be promoted to **Production Core**, the LLM Harness must meet the following criteria:

### 1. Robust Architecture & Real Execution
- **AgentClient Real**: No mock or stub client fallbacks are used in production. Real API calls are dispatched to registered providers.
- **Mock Provider Integration Tests**: The test suite must include at least one functional integration test verifying provider API payloads and responses (e.g., in `tests/integration/llm_harness/test_llm_harness_providers.py`).
- **No Versioned Compiled Files**: Absolutely no `.pyc` files or compiled cache files are tracked in the repository.

### 2. Sandbox Security & Lifecycle Governance
- **Docker Cleanup Real**: Container lifecycle must be managed safely. The sandbox must register signal handlers and `atexit` routines to execute `docker rm -f` on any active container.
- **No Hardcoded Paths**: Crucial paths (workspace mount path, temporary directories, report directories) must be fully customizable via config files, env variables, or CLI parameters.
- **No Magic Short-Circuits**: No implicit task matching (such as auto-succeeding tasks containing `"fix"`) is allowed in the production loop. Test short-circuits must be explicitly gated.

### 3. Safety, Secrets & Configuration Rules
- **Secrets Redaction Tested**: Event logs, reports, and payloads must undergo strict sanitization to redact API keys and bearer tokens. Tests must verify redactions.
- **Explicit Configuration Failure**: Invalid TOML, YAML, or configuration schema formats must cause explicit startup failure instead of falling back to defaults silently.
- **Validation Clean**: Linter (`ruff`), type checker (`mypy`), and test suite (`pytest`) must be fully green.

### 4. Continuous Verification & Providers
- **Providers Matrix Tested**: The test suite must contain provider matrix test coverage (`tests/integration/llm_harness/test_provider_matrix.py`) validating registered providers, minimum configuration, repr safety, and response formatting.
- **Check Script Validation**: Validation must be run through the automated script `scripts/validators/check-llm-harness-production-core.py` outputting compliance reports in JSON and Markdown format.

### 5. Advanced Runtime Capabilities (P0/P1 Roadmap)
- **Context Window Management**: Mandatory management of LLM context window to prevent overflow and ensure critical task context preservation.
- **Response Schema Validation**: Strict enforcement of Pydantic-based action schemas for all agent outputs.
- **Token Budgeting**: Integration of local token counting and real-time usage budgeting.
- **Cache Persistence & TTL**: Implementation of Time-to-Live and eviction policies for local cache.
- **Memory Storage Lifecycle**: Managed rotation and compression of execution history.

### 6. Production Quality, CI/CD, and Observability Gates
- **Coverage Gate**: Strict coverage enforcement on the harness module (minimum threshold of 75% coverage validated via `./scripts/validators/validate-llm-harness.sh`).
- **GitLab CI dedicated pipeline**: GitLab CI pipeline configured with dedicated linting, testing, typechecking, and regression benchmarking jobs.
- **Pre-commit integration**: Mandatory pre-commit configuration (`.pre-commit-config.yaml`) running checks for ruff (lint/format), mypy, and configuration schema sanitizers.
- **Ruff & Mypy Strictness**: Strict Mypy type-checking without global `ignore_missing_imports`, and expanded Ruff checks covering W, UP, B, SIM, ARG, and N rules.
- **Benchmark Regression Gating**: Benchmark harness runs verifying that performance/latency does not regress beyond a 10% tolerance threshold compared to `artifacts/benchmarks/llm-harness/baseline.json`.
- **OpenTelemetry Observability**: Spans instrumented across the CodingLoop (`run`, `llm_call`, `tool_call`, `policy_check`, `sandbox_run`, `eval_case`) verifying execution tracing, trace propagation, and secret sanitization.

### 7. Extensible Platform Capabilities (V2.2+ Release Gate additions)
To support the transition into a fully extensible agent platform, the production core readiness gate enforces the following validations:
- **REST Server Gate**: Rest API exposing GET `/health`, POST `/runs`, GET `/runs/{run_id}/events` (SSE), GET `/tools`, GET `/providers`, POST `/evals/run` and related endpoints. Verification checks that endpoints return status 200/OK and optional token authentication rejects request when configured.
- **Plugin Registry Gate**: Verified loading of dynamics plugins from `plugins.d/` and entry points. Core tools (like `read_file`, `plan`) are locked down from overrides, raising error if overwritten without explicit allow flag.
- **MCP Client Gate**: Verified loading of custom MCP client server definitions. Verification checks path boundary policy on all args, and sanitized metadata payload logging.
- **Benchmark Suite Gate**: Local benchmark adapter loading and comparisons of accuracy. Verification tests pass@1, duration, token calculations and threshold regression fails.
- **Multimodal Schema Gate**: Validation of multi-modal message formats. Verification tests that base64 image data is correctly formatted, checks that path resolves inside repository boundaries, and prevents leaked image data in reports.

