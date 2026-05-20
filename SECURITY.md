# Security

## Scope

`llm-inference-stack` is intended for local and controlled deployments. This document covers the default security posture, operational expectations, and release hardening checks for the `v1.9.8-platform-consolidation` line.

## Defaults

- Admin endpoints require `X-Admin-Token`.
- `RBAC_ADMIN_ENABLED=false` preserves the legacy admin-token flow; `RBAC_ADMIN_ENABLED=true` switches admin APIs to RBAC permission enforcement.
- Client inference and portal endpoints require `Authorization: Bearer <api_key>`.
- Demo API keys are stored hashed and are not emitted in application logs.
- The data plane is only exposed on the internal Docker network by default.
- Correlation IDs are propagated through request handling and responses.
- Security headers are added by the API/proxy layer.
- `PKI_ENABLED=false` and `HARDWARE_TRUST_ENABLED=false` do not block startup; PKI issuance and hardware trust checks remain disabled until explicitly enabled.
- Attestation defaults to advisory behavior, and plugin signature enforcement is opt-in.
- `DEPLOYMENT_MODE=appliance`, `KUBERNETES_MODE=false`, `DISTRIBUTED_RUNTIME_ENABLED=false`, `GPU_AUTOSCALING_ENABLED=false`, `PLUGIN_MARKETPLACE_ENABLED=false`, and `MANAGED_CONTROL_PLANE_ENABLED=false` keep enterprise runtime surfaces disabled by default.
- Managed control-plane routes are not mounted unless `MANAGED_CONTROL_PLANE_ENABLED=true` and `DEPLOYMENT_MODE=managed_control_plane`.

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

## Trust Controls

- PKI is local-only and operator-managed. Do not commit files from `PKI_STORAGE_PATH`, especially `*.key`, `*.pem`, `*.crt`, or CRLs generated during tests.
- Hardware trust and attestation should be treated as non-enforcing unless the corresponding config gates are enabled and validated in the target environment.

## Logging Policy

- Plaintext API keys must not be logged by the control plane.
- Admin tokens must not be returned by public or client-facing endpoints.
- Correlation IDs are safe to log and are intended for troubleshooting.
- If debug logging is enabled in production-like environments, review logs for prompt content and metadata retention before release.
- Managed control-plane heartbeats are limited to operational metadata. Prompt bodies, document content, and similar payload fields are rejected before persistence.
- **Supportability Pack Redaction**: Diagnostic bundles generated via `/admin/support/bundle` are automatically processed through a redaction engine. Regex patterns for `sk-...`, `ADMIN_TOKEN=...`, `JWT_SECRET=...`, and `Bearer ...` are intended to prevent sensitive keys, tokens, or PII from being exported in diagnostic logs or metadata.

## Managed Data Boundaries

- Local/offline Docker Compose remains the baseline deployment and does not require Kubernetes, operator mode, or managed SaaS services.
- Kubernetes/operator mode is optional and must be explicitly enabled out-of-band; no local/offline path depends on it.
- The plugin marketplace works offline with operator-supplied archives. No remote marketplace sync is required by default.
- GPU autoscaling defaults to advisory recommendations and is automatically disabled when distributed runtime is disabled.

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

## Multi-Cluster Data Boundaries
No cross-cluster operations exfiltrate user prompts or RAG documents by default. Synchronizations are limited to configuration metadata and health status.

## Observability Privacy
Metrics and dashboards (Grafana/Prometheus) are strictly audited to ensure no sensitive data (prompts, completions, API keys) is leaked into observability pipelines.

## Supply Chain Security
All releases include a Software Bill of Materials (SBOM) and are signed to ensure integrity. Lockfiles are enforced for all builds.

## Compliance Readiness
The platform includes an integrated SOC 2 and ISO 27001 readiness framework. Evidence collection is automated and sanitized to support internal preparation work only; this does not represent certification, attestation by an external auditor, or mandatory enforcement by default.

## Chaos Engineering Safety
Fault injection is strictly opt-in and blocked in production environments by default. Mandatory timeouts and rollback mechanisms prevent permanent service disruption.

## Reporting a Vulnerability

This project is local-first and does not have a public disclosure program yet. For internal use, document the issue, affected version, reproduction steps, and proposed mitigation in the release checklist before shipping changes.
