---
owner: platform-ops
status: consolidated
---

# Validation Strategy

## Smoke vs Full

The project distinguishes two validation modes:

- **Smoke** (`VALIDATION_MODE=smoke`): static checks, structural validators, and unit tests.
  Avoids long integration suites. Intended for daily use and quick feedback.
- **Full** (`VALIDATION_MODE=full`): runs the complete validation chain including
  slow integration tests. Preserves full coverage. Intended for CI, releases, and
  pre-merge gates.

## When to Use Each Target

| Target | Mode | Use Case |
|---|---|---|
| `validate-architecture-smoke` | smoke | Daily development, pre-commit |
| `validate-architecture-full` | full | CI, releases, pre-merge |
| `validate-architecture` (legacy) | full | Backward-compatible alias for `full` |
| `validate-platform` | full | Platform-wide aggregate (composes full targets) |
| Individual `validate-phase-XX-*` | full | Debugging a specific phase |

## Running by Group

```bash
make validate-makefile-governance          # Makefile structure
make validate-governance-documentation-foundation  # Docs foundation
make validate-domain-contracts             # Domain contracts
make validate-claims                       # Prohibited claims
make validate-platform-architecture        # Platform architecture
make validate-phase-82-platform-sustainability  # Phase 82 sustainability
```

## VALIDATION_MODE Environment Variable

Legacy targets default to `full`. New smoke-only targets use `smoke`.

```bash
VALIDATION_MODE=smoke make validate-architecture-smoke
VALIDATION_MODE=full  make validate-architecture-full
```

## Policy for New Targets

1. Every new aggregate must have an explicit `-smoke` and `-full` variant.
2. Smoke variants must complete in under 5 minutes.
3. Static validators (script-only, no DB) belong in smoke.
4. Integration tests (DB, API, fixtures) belong in full only.
5. Add the target to the appropriate group variable in the Makefile.

## Policy for Slow Tests

1. Tests taking >30s are candidates for `@pytest.mark.slow`.
2. Slow tests must be excluded from smoke runs.
3. Use `scripts/dev/list_slow_tests.py` to identify candidates.
4. Do not delete slow tests — segregate them behind the smoke/full boundary.

## Policy for Not Masking Failures

1. Smoke must never silence failures that full would catch.
2. Smoke is a strict subset of full.
3. Every smoke target has a corresponding full target with wider coverage.
4. CI must run full before merging.

## Offline-First Expectation

All validation targets must work without:
- Internet access
- External API calls
- Cloud dependencies
- Paid services

No target may introduce mandatory network dependencies.
