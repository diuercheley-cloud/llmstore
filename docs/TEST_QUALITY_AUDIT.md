# Cosmetic Test Audit (Sample)

## Identified Cosmetic Tests
- `tests/unit/core/test_config_service.py`: High mocking of environment variables, low value. Slated for replacement with real precedence tests.
- `tests/api/test_public_routes.py`: High mocking of `FastAPI` context, minimal validation of real handler logic.

## Recommended CI Pipeline Adjustments
Update `.gitlab/ci/` to trigger pipelines based on markers:
- **Unit Pipeline**: Runs tests marked `unit`.
- **Integration Pipeline**: Runs tests marked `integration`.
- **Security Pipeline**: Runs tests marked `security`.
- **Release Gate**: Runs tests marked `release_gate`.

(Use `pytest -m unit`, `pytest -m integration`, etc. in the respective CI jobs)
