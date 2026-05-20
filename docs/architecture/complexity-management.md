# Platform Complexity Management Architecture

This document outlines the architectural strategy for managing, monitoring, and reducing complexity within the `llm-inference-stack` platform.

## Goal

As platforms evolve, they risk experiencing architectural drift and horizontal complexity explosion (e.g., redundant scripts, untested logic paths, undocumented configuration parameters). This policy establishes a systematic approach to identify, classify, and prioritize refactoring candidates without compromising backward compatibility.

---

## Metric Definitions

The platform complexity analyzer gathers static metrics across the following vectors:

1. **API Surface**:
   - **Routers & Endpoints**: Total routing handlers. A high density indicates high-exposure risk.
   - **Deprecated Endpoints**: Route handlers marked `deprecated=True`.
   - **Internal Endpoints**: Route handlers marked with `tags=["internal"]` or paths `/internal/`.

2. **Core Logic**:
   - **Services**: Classes and methods containing domain logic.
   - **Test Gaps**: Services lacking corresponding test modules under `control_plane/tests/`.

3. **Data Schemas**:
   - **Database Models**: SQLAlchemy classes subclassing `Base`.

4. **Automation & Operations**:
   - **Scripts**: Utility scripts under `scripts/`.
   - **Script Duplication**: Redundant files determined by identical SHA-256 hashes.
   - **Make Targets**: Available orchestration targets in `Makefile`.

5. **Configuration**:
   - **Feature Flags**: Mapped keys in `config/feature-flags.yaml`.
   - **Orphan Flags**: Registered flags with zero references in Python code or environments.

---

## Action Classification Schema

Every refactoring recommendation is classified under one of the following labels:

- **`safe cleanup`**:
  - *Definition*: Actionable and high-safety cleanup.
  - *Examples*: Identical script duplicates, orphaned feature flags.
  - *Risk*: Negligible.

- **`needs compatibility shim`**:
  - *Definition*: Legacy/deprecated elements still in active use by external client integrations.
  - *Examples*: Active deprecated endpoints, undocumented docs files.
  - *Risk*: Moderate. Requires deprecation warnings and grace periods before final deletion.

- **`deprecated candidate`**:
  - *Definition*: Components that are marked for deprecation but still require scheduling or migration path creation.
  - *Examples*: Services with no usage references, deprecated feature flags.
  - *Risk*: Moderate. Requires testing in staging environments.

- **`merge candidate`**:
  - *Definition*: Duplicate/redundant code structures with slight differences.
  - *Examples*: Overlapping helper scripts or APIs.
  - *Risk*: High. Requires careful code union and testing.

- **`archive candidate`**:
  - *Definition*: Outdated artifacts and release scripts.
  - *Examples*: Release checklist scripts for version `< v1.9`.
  - *Risk*: Low. Can be safely archived to a `/legacy` folder or git history.

- **`do not touch`**:
  - *Definition*: Critical path architectures under strict freeze governance.
  - *Examples*: Platform freeze logic, core routers, base db configuration.
  - *Risk*: Critical. Never modify during stabilization.

---

## Governance Workflow

1. **Automatic Reports**: Triggered by running `make complexity-report`.
2. **Review & Approve**: The reports generated under `artifacts/complexity/latest/` must be analyzed during quarterly stabilization phases.
3. **Execution**: No script may automatically delete files. All cleanup actions must be performed manually and verified by unit tests.
