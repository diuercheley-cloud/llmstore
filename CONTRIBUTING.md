# Contributing

## Quick Start

```bash
# 1. Clone and enter
git clone <repo> && cd llm-inference-stack

# 2. Setup
make install              # system deps + Python venv
cp .env.example .env.local && source .venv/bin/activate

# 3. Run database migrations
alembic upgrade head

# 4. Start the stack
docker compose up -d postgres redis
make run                  # uvicorn dev server on :8080
```

## Project Structure

```
control_plane/            # FastAPI backend
  app/
    api/                  # Route handlers
    services/             # Business logic
      agents/             # Agent runtime & ecosystem
      providers/          # LLM providers (OpenAI, Anthropic, etc.)
    models/               # SQLAlchemy models
    core/                 # Config, settings
    middleware.py          # HTTP middleware (security, rate limiting)
frontend/                 # Admin dashboard (React 19 + Vite)
  admin/                  # Admin SPA
  client/                 # Customer portal (PWA)
sdk/                      # Client SDKs
  python/                 # Python SDK
  node/                   # TypeScript SDK
deploy/                   # Deployment
  helm/                   # Kubernetes Helm chart
  kubernetes/             # Raw K8s manifests
docker/                   # Dockerfiles
docs/                     # Documentation
scripts/                  # Operational scripts
tests/                    # Test suite
```

## Development

### Code Style
- Python: `ruff check . && ruff format .`
- TypeScript: `cd frontend/admin && npx tsc --noEmit`
- Run before committing: `make lint`

### Testing
```bash
make test                 # all tests
make test-unit            # unit tests only
make test-services        # service tests
cd frontend/admin && npx vitest run
```

### Adding an LLM Provider
1. Create `control_plane/app/services/providers/<name>_provider.py`
2. Implement `ProviderAdapter` abstract methods
3. Add `ProviderType` enum in `base.py`
4. Register in `registry.py`
5. Add config fields to `app/core/config.py`

### Making API Changes
1. Add route in `app/api/` with proper tags
2. Add Pydantic schemas for request/response
3. Update `app/main.py` to include the router
4. Add tests in `tests/api/`

## Pull Request Process
1. Branch from `main`: `feature/description` or `fix/description`
2. Keep changes focused — one feature per PR
3. Update tests and docs
4. Verify `make release-gate` passes (all gates, no failures)
5. Request review from a maintainer

## Code of Conduct
Be respectful, constructive, and inclusive. Harassment or toxic behavior will not be tolerated.

## License
See [LICENSE](LICENSE).
