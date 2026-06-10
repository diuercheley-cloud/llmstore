---
owner: platform-ops
status: consolidated
---

# Platform Operations Runbook

## Prerequisites

- Python 3.10+
- Make
- Git hooks installed (optional but recommended)

## Smoke Validation Workflow

```bash
make validate-architecture-smoke
```

This runs the fast validation path — static checks and short tests only. Expected duration: seconds.

**What it validates:**
1. Makefile governance structure
2. Governance documentation foundation
3. Domain contracts
4. Prohibited claims
5. Platform architecture
6. Architecture boundaries
7. Runtime contracts
8. Invariants
9. ADRs
10. Phase 69–82 validator scripts (smoke mode)

## Full Validation Workflow

```bash
make validate-architecture-full
```

Runs all validators including integration tests. Expected duration: minutes.

**What it validates:**
- All smoke validation checks
- Phase 66 readiness gate
- Full phase validators (Phase 69–82) with pytest suites
- Deterministic event architecture
- Governance core
- Disaster recovery readiness

## Documentation Validation Workflow

```bash
make validate-platform-documentation
```

Validates documentation completeness and consistency.

**What it validates:**
- Required docs exist
- README has required sections
- Glossary contains required terms
- Phase timeline covers Phases 69–82
- Explicit limitations are present
- No prohibited claims exist
- Internal links are valid (basic check)

## Troubleshooting

### Validation fails: "Claims validation failed"

The claims validator found prohibited language in documentation or scripts:

```bash
# Run claims validator directly to see details
python3 scripts/validators/validate_claims.py
```

Common prohibited claim issues:
- `military-grade` or similar phrasing must not appear
- `guaranteed secure` or absolute security claims must not appear
- `certified` without evidence must not appear

### Validation fails: "Architecture boundaries validation failed"

One or more bounded context rules are violated:

```bash
# Run boundaries validator directly
python3 scripts/validators/validate_architecture_boundaries.py
```

Check:
- No circular dependencies between contexts
- All cross-context references use explicit contracts
- No context has unauthorized access to another's internals

### Validation fails: "Documentation validation failed"

Run the documentation validator directly:

```bash
python3 scripts/validators/validate_platform_documentation.py
pytest tests/integration/docs/test_platform_documentation.py -v
```

## Reading Reports

### Validation Reports
Each phase validator produces a structured report:
- Exit code 0: All checks passed
- Exit code 1: One or more checks failed
- Output includes specific failure details

### Replay Verification Reports
Replay verification confirms event log consistency:
- **PASS**: All events replayable, no divergence
- **FAIL**: Event chain broken or non-deterministic

To interpret:
1. Check which event sequence failed
2. Verify event schema version matches
3. Confirm no external state influenced replay

### Lineage / Provenance Reports
Artifact lineage shows the chain of custody:
- Source hash
- Build environment fingerprint
- Verification receipts
- Chain of transformations

If verification fails:
1. Check source artifact hash
2. Verify build environment matches recorded policy
3. Check for intermediate modifications

### Policy Engine Reports
Governance policy evaluation produces:
- Policy bundle version
- Rules evaluated
- Decisions (pass/warn/block)
- Justification for each decision

Policy reports are advisory by default. "Block" decisions require operator override to proceed.

## Operational Commands Reference

| Command | Description |
|---------|-------------|
| `make validate-architecture-smoke` | Fast validation path |
| `make validate-architecture-full` | Complete validation |
| `make validate-platform-documentation` | Documentation validation |
| `make validate-platform` | Full platform validation |
| `make health` | Stack health check |
| `make backup` | Local backup |
| `make restore BACKUP_DIR=<dir>` | Restore from backup |
