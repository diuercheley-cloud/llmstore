# Production Evaluation Gates

> Owner: agent-platform | Status: Stable

The evaluation gates system ensures that only high-quality, secure, and compliant agents are promoted to production (`active` status).

## Mandatory Evaluation Checks

Every evaluation suite run must pass a set of core quality and security compliance assertions:

1. **Structured Output:** Final answers are verified to match structured outputs (such as valid JSON).
2. **Tool Selection:** Correct tools must be selected by the agent as requested.
3. **Memory Use:** Detects and verifies correct reads/writes of memory steps.
4. **Policy Compliance:** Scans for any compliance denials during execution steps.
5. **Multi-Step Completion:** Ensures the agent completes multi-step workflows when required.
6. **No Secret Output:** Scans output data for API keys, tokens, passwords, and sensitive credentials to prevent leaks.
7. **Tenant Isolation:** Validates that execution was properly scoped and no cross-tenant metadata references exist.

---

## Gate Rules and Feature Flags

- `AGENT_EVAL_GATE_STRICT`: When `true` (default), strict enforcement is applied. Under strict mode, safety failures (such as secret leak detection or cross-tenant isolation breaches) strictly fail the gate and cannot be bypassed via audit overrides.
- `AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE`: Requires a valid evaluation baseline to be run before an agent can be approved or activated.
- `AGENT_EVAL_REGRESSION_GATE_ENABLED`: When enabled (`true`), checks that the promotion run does not regression compared to the baseline score.

---

## Promotion Decision Logic

When evaluating promotion to `"active"` status:

1. **Baseline Validity:** The agent must have an existing non-stale baseline.
2. **Golden Case Check:** All defined golden test cases must pass.
3. **Safety Violations:** Any detected secret leaks or cross-tenant access violations block promotion under strict gating.
4. **Mock Provider Guard:** Runs executed using the `mock` provider are blocked from promotion to production unless `AGENT_EVAL_ALLOW_MOCK_FOR_PROMOTION` is set to `true`.
5. **Regression Verification:** Quality metrics (pass rate, latency, cost) must not regress below baseline tolerances.
