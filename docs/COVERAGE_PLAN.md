# Code Coverage Progressive Plan

## Current Status (v2.1.0)
- **Global Coverage**: 37%
- **Target Coverage**: 90%
- **Current Enforcement**: 37%

## Progressive Ratchet Plan
To reach the 90% goal without breaking development velocity, we will apply a progressive ratchet:
- **Baseline**: 37% (Immediate)
- **Increment**: +1% per sprint (bi-weekly)
- **Expected 90% Achievement**: ~12 months

| Milestone | Target Coverage | Date |
|-----------|-----------------|------|
| M1 | 40% | Sprint 1 |
| M2 | 50% | Sprint 13 |
| M3 | 75% | Sprint 38 |
| M4 | 90% | Sprint 53 |

## Critical Module Targets
The following modules are high-risk and must maintain **90% coverage immediately**. Any PR modifying these files must not decrease their individual coverage.

| Module | Purpose | Current Coverage |
|--------|---------|------------------|
| `control_plane/app/services/security/` | Auth, PKI, Encryption | ~20% (Urgent Action Required) |
| `control_plane/app/core/config_service.py` | Configuration | 42% |
| `control_plane/app/services/cache/` | Semantic Cache | 85% |

## Enforcement Strategy
1. **CI Integration**: `pytest --cov` will run on every PR.
2. **Ratchet Enforcement**: `fail_under` in `pyproject.toml` will be updated manually by the Release Engineer at the end of each sprint.
3. **New Code Rule**: All new code must be submitted with at least 80% unit test coverage.
4. **Bug Fixes**: Every bug fix must include a regression test.

## Coverage Gaps Analysis
- **Missing Scripts**: Many shell scripts in `scripts/` are not currently tracked by Python coverage.
- **Async Workers**: `control_plane/app/workers/` currently has 0% coverage.
- **Provider Adapters**: `scripts/llm_harness/providers.py` has very low coverage due to lack of mock-provider tests.

## Technical Debt & Infrastructure
- **Collection Errors**: Currently, several integration tests fail during collection when running from the root due to missing dependencies in the local environment (e.g., `openai_real_validator`). This interferes with global coverage reporting.
- **Pathing**: The project uses a mix of root-level and subdirectory-level imports, requiring `PYTHONPATH=.:control_plane` for consistent execution.
