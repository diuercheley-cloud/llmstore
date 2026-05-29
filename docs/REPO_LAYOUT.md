---
owner: platform-ops
status: consolidated
---

# Repository Layout Policy

This document defines the organization of files and directories in the `llm-inference-stack` repository.

## Directory Structure

| Directory | Content Description |
|-----------|---------------------|
| `/` (Root) | Configuration files, main entry points (if any), and core project metadata. |
| `scripts/` | Shell scripts and Python executable utilities used for management, deployment, and validation. |
| `scripts/lib/` | Shared shell libraries (sourced by scripts via SCRIPT_DIR or PROJECT_ROOT). |
| `control_plane/` | Source code for the control plane application. |
| `data_plane_mock/` | Mock implementation of the data plane for development/testing. |
| `docs/` | Project documentation, runbooks, and architectural guides. |
| `tests/` | Automated tests (unit, integration, e2e). |
| `docker/` | Dockerfiles and container-specific configurations. |
| `config/` | Example and default configuration files. |
| `artifacts/` | Generated files, logs, and audit reports (ignored by git). |

## Python File Policy

To keep the repository root clean, Python files should be placed according to their purpose:

### Executable Scripts
All Python files intended to be run directly by the user or by other scripts should reside in `scripts/`.
- **Naming:** Prefer `snake_case.py`.
- **Examples:** `benchmark_runner.py`, `redact_json.py`.

### Library Code
- Internal libraries used by the control plane should stay within `control_plane/app/`.
- General-purpose Python utilities used by multiple components or scripts should reside in `scripts/` if they are primarily support for shell scripts, or potentially a dedicated `python_lib/` if the volume grows.

### Test Utilities
Python files that are strictly for testing purposes and are not part of the production or management workflow should reside in `tests/`.

## Prohibited in Root
- No utility Python scripts.
- No temporary files or logs.
- No `__init__.py` unless the entire repository is intended to be a single Python package (not the case here).

## Shell Library Import Policy

Shell libraries live in `scripts/lib/` and MUST be sourced using one of these patterns:

**From scripts/ directly:**
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/redaction.sh"
```

**From scripts/ using PROJECT_ROOT (via common.sh):**
```bash
source "${ROOT_DIR}/scripts/lib/operator-errors.sh"
```

The following are PROHIBITED:
- `source` with `$(dirname "$0")` (fragile when script is called from other directories)
- `source` with `../lib/` relative paths
- Direct `lib/` root imports after migration to `scripts/lib/`

## Repo Path Validation

Run `scripts/validate-repo-paths-local.sh` to check for broken references:
- Invalid shell script shebangs
- Missing file targets in `source` statements
- Python scripts referenced from shell that do not exist
- Makefile targets pointing to missing scripts
- Shell syntax errors via `bash -n`
- Python compile errors via `py_compile`

To suggest or apply fixes for path issues:
```bash
scripts/fix-repo-paths-local.sh          # dry-run
scripts/fix-repo-paths-local.sh --apply  # apply safe substitutions
```

Reports are generated in `artifacts/repo-cleanup/<timestamp>/`.

## Exceptions
- `llm_stack_client.py` may remain in the root (optional) to facilitate easy import for end-users, or reside in `scripts/` as a reference implementation. *Current decision: scripts/*
