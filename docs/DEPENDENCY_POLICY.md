# Dependency Policy

## 1. Python
- **Source of Truth**: `pyproject.toml` (unified for backend and tools).
- **Tooling**: `uv` (mandatory for installations, locking, and management).
- **Lockfile**: `uv.lock`.
- **Policy**: `requirements.txt` files are deprecated and MUST NOT be used for new dependencies. Existing `requirements.txt` should be migrated to `pyproject.toml`.

## 2. Node.js
- **Source of Truth**: Root `package.json` with `workspaces` config.
- **Tooling**: `npm` (workspaces).
- **Workspaces**:
  - `frontend/admin`
  - `frontend/client`
  - `sdk/node`
- **Policy**: All Node modules must be managed via root `npm` commands (`npm install`, `npm run ...` with `--workspace`).

## 3. Standardization
- **Backend Lint/Test**: `make lint`, `make test` (run `ruff`, `pytest` via `uv run`).
- **Frontend Lint/Test/Build**: `npm run lint --workspace=<name>`, `npm run test --workspace=<name>`, `npm run build --workspace=<name>`.
- **SDK Build**: `npm run build --workspace=sdk/node` (Node), `python -m build` (Python).

## 4. Publication Gate
- SDK publication is only triggered by GitHub Actions on tagged releases, after all `release_gate` tests pass.
- Dry-runs are mandatory for local publication testing.
