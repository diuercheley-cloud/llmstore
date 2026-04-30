# Security

## Scope

`llm-inference-stack` is intended for local and controlled deployments. This document covers the default security posture, operational expectations, and release hardening checks for `0.2.0-local`.

## Defaults

- Admin endpoints require `X-Admin-Token`.
- Client inference and portal endpoints require `Authorization: Bearer <api_key>`.
- Demo API keys are stored hashed and are not emitted in application logs.
- The data plane is only exposed on the internal Docker network by default.
- Correlation IDs are propagated through request handling and responses.
- Security headers are added by the API/proxy layer.

## Secrets Handling

- Keep `.env.local` or `.env` outside version control.
- Use non-default values for `ADMIN_TOKEN`, `POSTGRES_PASSWORD`, and any external provider credentials.
- Local env files should be readable only by the current user: `chmod 600 .env.local`.
- Avoid pasting API keys into shell history when possible. Prefer environment variables exported for the current shell session.

## Key Rotation

- Client API keys can be rotated by creating a new key and revoking the previous one through `POST /admin/api-keys/{id}/rotate`.
- The plaintext of a client API key is returned only on creation or rotation. Listing endpoints expose `key_prefix` only.
- Rotate `ADMIN_TOKEN` by editing `.env.local`, replacing the old token with a new strong value, confirming the file remains `chmod 600`, and restarting the stack with `docker compose up -d`.
- For public-facing deployments, use a token with at least 24 characters and mixed character classes.

## Logging Policy

- Plaintext API keys must not be logged by the control plane.
- Admin tokens must not be returned by public or client-facing endpoints.
- Correlation IDs are safe to log and are intended for troubleshooting.
- If debug logging is enabled in production-like environments, review logs for prompt content and metadata retention before release.

## Network Exposure

- Publish only the reverse proxy/control-plane port externally.
- Do not publish data-plane ports directly unless there is an explicit network boundary and authentication layer in front of them.
- Restrict admin endpoints to trusted operators and networks.

## CORS

- CORS is deny-by-default unless `CORS_ALLOW_ORIGINS` is explicitly configured.
- Keep CORS restricted to known portal/admin origins.
- Do not use wildcard origins with credentialed browser access in shared or internet-facing environments.

## Abuse Controls

- Monitor `security_events` for invalid API key bursts, repeated large prompts, abnormal error spikes, and plan abuse.
- Suspend compromised or abusive clients through the admin security endpoints.
- Keep per-client rate limits and token quotas aligned with each billing plan.

## Reporting A Vulnerability

This project is local-first and does not have a public disclosure program yet. For internal use, document the issue, affected version, reproduction steps, and proposed mitigation in the release checklist before shipping changes.
