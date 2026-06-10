# Release Checklist

## Versioning

- Confirm `VERSION` matches the intended release.
- Review changelog/release notes if maintained separately.

## Security

- Verify `.env.example` contains no real secrets.
- Verify `.env.local` or `.env` uses non-default secrets.
- Verify `.env.local` or `.env` is `chmod 600`.
- Confirm `ADMIN_TOKEN` rotation procedure is documented and tested operationally.
- Confirm control-plane logs do not contain plaintext API keys or admin tokens.
- Confirm client portal does not reference or expose admin auth semantics.
- Confirm data-plane services are not published externally by default.
- Confirm security headers and correlation ID response headers are present.
- Review CORS configuration for the target environment.
- If `PUBLIC_EXPOSURE=true`, confirm `ADMIN_TOKEN` is strong and `/admin-dashboard` is not publicly served.

## Product Flows

- Sync chat request works.
- Async queue, status, and cancel flows work.
- API key rotation and revocation work.
- Billing cycle and invoice endpoints work.
- Cache, retry, and fallback behavior do not duplicate billing.
- Portal login by API key works.
- Admin exports and monthly reports work.

## Limits And Safety

- Rate limit enforcement is active.
- Daily and monthly quotas are enforced.
- `max_tokens` and context limits are enforced.
- Backend concurrency defaults remain safe for the target GPU.
- Abuse/security event detection is active.

## Installation And Operations

- `scripts/deploy/install.sh` completes on a clean Linux/WSL2 host.
- `scripts/deploy/first-run.sh` completes and prints usable URLs.
- `scripts/dev/reset-dev.sh` still requires explicit confirmation.
- `make install`, `make up`, `make down`, `make validate`, `make backup`, and `make logs` are functional.
- Backup includes PostgreSQL, env file, `VERSION`, docker configs, model manifest, and checksums.
- Restore validates version/schema and does not overwrite `.env.local` without confirmation.
- `./scripts/dev/dr-test.sh` completes from a recent backup.
- `docs/INSTALL.md`, `docs/OPERATIONS.md`, and `docs/TROUBLESHOOTING.md` match the current stack behavior.

## Validation

- `pytest`
- `./scripts/validators/validate-e2e.sh`
- `make validate`
