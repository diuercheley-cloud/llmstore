# Working Tree Certification — v2.x-agentic-consolidation-hardening

**Generated at**: 2026-05-28T20:50:48Z  
**Git SHA**: 0b207e2cbd34ac28d57efb5337ca25ffc8fe35e8  
**State**: dirty_non_blocking  
**Overall**: FAIL  

## Check Results

| Check | Result | Description |
|-------|--------|-------------|
| git-status-clean | FAIL | No uncommitted changes |
| no-unstaged-changes | PASS | Index matches HEAD |
| no-critical-untracked | FAIL | No untracked files outside artifacts/ |
| no-debug-leftovers | PASS | No core dumps, logs, stacktraces |
| artifacts-in-policy | PASS | All artifacts under artifacts/ directory |
| no-secrets-untracked | PASS | No key/pem/cert/secret files untracked |
| no-runtime-dumps | PASS | No .prof, .lprof, .pid, .trace files |

## State Definition

- **clean**: Working tree perfectly clean — zero dirty files.
- **clean_with_allowed_local**: Clean except for explicitly allowed local environment files.
- **dirty_non_blocking**: Dirty only with allowed runtime artifacts (under `artifacts/`).
- **dirty_blocking**: Dirty with forbidden or unclassified files.

## Failures

\n  - git-status-clean\n  - no-critical-untracked

## Criteria

- **Release final must reach**: `clean` or `clean_with_allowed_local`

