# LLM Harness Release Gate

**Formal acceptance criteria and security gates for the modular LLM Harness.**

## Release Readiness Criteria

The LLM Harness is considered ready for promotion to `Production Core` only when all the following gates pass.

### 1. Security & Isolation Gate
- [ ] **Sandbox Hardening**: Code execution must be fully isolated. No network access by default.
- [ ] **Sanitization**: 100% pass rate on prompt injection and markdown escape test suites.
- [ ] **Secret Scanning**: No leaked API keys or credentials in agent traces or logs.
- [ ] **Policy Enforcement**: Runtime limits (tokens/cost) must be strictly enforced with zero bypass.

### 2. Functional & Integration Gate
- [ ] **Control Plane Connectivity**: Successful communication with `agent-registry` and `governance` services.
- [ ] **Coding Loop Stability**: Successful completion of the "Standard Fix" benchmark (reproducing and fixing a known bug).
- [ ] **Tool Coverage**: All core tools (files, git, shell, tests) must have 100% unit test coverage.
- [ ] **Comprehensive Testing**: All consolidated tests in `tests/llm_harness/` must pass.
- [ ] **CLI Completeness**: All documented commands must be functional and return correct exit codes.

### 3. Observability & Audit Gate
- [ ] **Structured Logging**: All agent actions must emit structured JSON logs with trace IDs.
- [ ] **Reporting**: Automated generation of `REPORTS_SUMMARY.md` after each test run.
- [ ] **Audit Receipts**: Successful persistence of execution receipts in the Control Plane audit trail.

### 4. Performance & Reliability Gate
- [ ] **Memory Management**: Workspace cleanup must be guaranteed after every execution (no orphan files).
- [ ] **Timeout Governance**: Agents must respect `EXECUTION_TIMEOUT` without hanging processes.
- [ ] **Error Handling**: Graceful degradation when the Control Plane or LLM provider is unavailable.

## Validation Commands

```bash
# Run the isolated release gate
make release-gate-llm-harness

# Run full security and sandbox tests
make agent-security-tests

# Validate documentation and consistency
make validate-platform-documentation
```

## Promotion Path

1.  **Experimental**: Local development, manual testing.
2.  **Beta**: Integrated with CI/CD, running on mock data.
3.  **Production Optional**: Enabled via feature flag `LLM_HARNESS_ENABLED=true`.
4.  **Production Core**: Default enabled, mandatory for all agentic workflows.

---
*Last Updated: 2026-06-03*
