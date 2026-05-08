# Test Fixtures

Main fixtures in `tests/conftest.py`:

- `fake_redis`: async in-memory Redis double for queue, cache and TTL behavior.
- `isolated_db_url`: temporary SQLite URL for isolated database-backed tests.
- `fastapi_app`: minimal FastAPI app fixture for transport-level tests.
- `async_client`: `httpx.AsyncClient` bound to `fastapi_app`.
- `app_client_factory`: builds an in-process `httpx.AsyncClient` for any FastAPI app under test.
- `admin_token_headers`: default admin token headers for admin endpoint tests.
- `models_dir`: temporary models directory patched into admin model management helpers.
- `admin_client`: application client with database and Redis dependencies overridden for tests.

Container pytest notes:

- The control-plane test image includes `README.md`, `docs/`, `examples/`, `demo/`, `.env.example`, `.gitignore` and `.githooks/` so documentation and operational tests can run inside the container.
- `git` and `jq` are installed in the image because several validation and security tests depend on them.
