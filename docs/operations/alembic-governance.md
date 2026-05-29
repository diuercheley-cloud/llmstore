---
owner: platform-ops
status: consolidated
---

# Alembic Migrations Governance & Graph Integrity

This document outlines the design principles, workflow requirements, and automated validation gates for database migrations in the LLM Inference Stack.

## 1. Governance Principles

To ensure database consistency, schema reliability, and zero-downtime upgrades, we enforce a strict linear migration history.

### 1.1 Single Head Rule
The repository must **always** contain exactly **one** Alembic migration head. Multiple heads (splits in the migration graph) are strictly prohibited in the main branch. Any feature branch that introduces a new migration must either build sequentially on the latest head or merge branches explicitly using `alembic merge`.

### 1.2 No Duplicate Revision IDs
Each migration file must have a unique `Revision ID`. Revisions must not be copied or duplicated.

### 1.3 Chain Continuity
Every migration (except the base initial schema migration) must point to a valid, existing `down_revision`. Graph links must be fully connected, with no orphan nodes or cycle loops.

---

## 2. Validation Gates

Integrity checks are fully automated and run at multiple stages of the development cycle.

### 2.1 Automated Script: `check-alembic-integrity.sh`
The `scripts/check-alembic-integrity.sh` validator performs a graph-theoretic validation of the migrations:
1. **Walks the graph**: Walks all revisions to detect loops/cycles.
2. **Checks heads**: Asserts that `len(heads) == 1`.
3. **Validates uniqueness**: Ensures no duplicate revision IDs are defined across files.
4. **Verifies continuity**: Confirms that all `down_revision` references point to known nodes.

### 2.2 Makefile Integration
- **`make validate`**: Runs `scripts/validate-local-production-full.sh` which executes the integrity script.
- **`make stabilization-check`**: Runs the formal release stabilization suite including Alembic checks.
- **`make validate-migrations`**: Runs `scripts/validate-migrations-local.sh`.

### 2.3 Pytest Verification
- **Test File**: `tests/build/test_alembic_integrity.py`
- Runs in CI to assert that the integrity validation exits with code `0`.

---

## 3. Resolving Conflicts (Multiple Heads)

If a merge conflict introduces multiple heads, resolve them using one of the following methods:

### Method A: Automated Merge
Generate a merge migration merging all existing heads:
```bash
cd control_plane
../.venv/bin/alembic merge <head_id_1> <head_id_2> -m "Merge heads"
```

### Method B: Manual Rebase
Change the `down_revision` of your new migration to point to the newest head introduced by the other branch, making the chain linear.
