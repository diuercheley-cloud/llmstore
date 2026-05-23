# Security

## Scope

`llm-inference-stack` is intended for local and controlled deployments. This document covers the default security posture, operational expectations, and release hardening checks for the `v2.0.2-agentic-ga-readiness` line.

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
- The security posture and active features are partially driven by `DEPLOYMENT_MODE`.
- In `appliance` mode (default), the agentic runtime is completely disabled and SaaS external connectors are blocked.
- In `pilot` mode, the agentic runtime is active but SaaS connectors are read-only (writes blocked), and any mutating tool or memory action strictly requires human operator approval (`AGENT_HUMAN_APPROVAL_ENABLED=true`). Strict resource budgets are enforced.
- In `production` mode, automatic evaluation gates are strictly enforced (`AGENT_PROMOTION_REQUIRES_EVALS=true` and `AGENT_EVAL_REGRESSION_GATE_ENABLED=true`) to block unvalidated agents.
- In `enterprise_managed` mode, the same production gates apply, supplemented by strict cryptographic tenant isolation (`AGENT_TENANT_ISOLATION_STRICT=true`), managed control plane constraints, and enterprise observability.
- `AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=false` is the expected GA posture. Any production override is a release blocker.
- Unsupported task simulation paths must fail closed. Completed task outputs must carry explicit `execution_mode`.
- Managed control-plane routes are not mounted unless `MANAGED_CONTROL_PLANE_ENABLED=true` and `DEPLOYMENT_MODE=enterprise_managed`.

## Agentic release controls

- Governed SaaS connectors require explicit enablement before any external network use or write action is possible.
- Stateful workflows must wake from persisted timers, signals, webhooks, or polling instead of pinning a worker for the entire wait period.
- Reasoning loops must repair malformed structured output and compress context before escalating to fallback behavior.
- Multi-agent orchestration must remain bounded by topology flags and governance controls for hierarchical and debate teams.
- Agent Studio visual authoring and debugger surfaces remain operator-only and disabled until explicitly enabled.
- Runtime, tool, and memory contracts are versioned and validated before promotion.
- Worker and queue execution are official but opt-in; no background worker starts unless `AGENT_WORKER_ENABLED=true`.
- Promotion remains blocked on failed or missing eval evidence even if runtime APIs are enabled.
- SLOs, metrics, readiness checks, and incident playbooks are required operator controls for the agentic surface.
- Provider validation is opt-in, budgeted, and must use synthetic data. GA evidence only counts when a non-mock provider/gateway actually answers a passing `basic_model_call`.

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
- Agent approvals, traces, replays, and memory workflows must not expose raw prompts by default; sanitized payloads and hashes are the baseline expectation.
- Agent runs must remain audit-reconstructable end to end: plan, tool call, memory access, approval, and terminal status all require durable timeline evidence.
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

## Agentic Data Boundaries
- Agent memory is tenant-scoped and disabled by default.
- Cross-tenant memory sharing is not supported.
- `/v1/agents` is the canonical tenant runtime API and `/agents` is deprecated for admin-only legacy compatibility.
- Destructive tools remain disabled unless explicitly enabled and separately approval-gated.
- Agent marketplace installs are offline-first and disabled by default.
- Multi-agent delegation remains disabled by default and is outside the default-supported posture for this release.

## Observability Privacy
Metrics and dashboards (Grafana/Prometheus) are strictly audited to ensure no sensitive data (prompts, completions, API keys) is leaked into observability pipelines.

## Supply Chain Security
All releases include a Software Bill of Materials (SBOM) and are signed to ensure integrity. Lockfiles are enforced for all builds.

## Compliance Readiness
The platform includes an integrated SOC 2 and ISO 27001 readiness framework. Evidence collection is automated and sanitized to support internal preparation work only; this does not represent certification, attestation by an external auditor, or mandatory enforcement by default.

## Chaos Engineering Safety
Fault injection is strictly opt-in and blocked in production environments by default. Mandatory timeouts and rollback mechanisms prevent permanent service disruption.

## Security Posture

- **Sovereign First**: All data and models reside within the operator's perimeter.
- **Agent Sandbox**: All agent tools execute in a controlled sandbox with mandatory credential delegation.
- **Isolated Memory**: Multi-tenant memory isolation ensures no cross-tenant data leakage.
- **Audit Trails**: Every reasoning step, tool call, and policy decision is cryptographically signed and archived.
- **Versioned Contracts**: Runtime, tool, and memory payloads are validated against versioned contracts before being treated as supported surface.
- **Production Gates**: High-risk agents require explicit evaluation baselines and human review before production activation.

## Reporting a Vulnerability

This project is local-first and does not have a public disclosure program yet. For internal use, document the issue, affected version, reproduction steps, and proposed mitigation in the release checklist before shipping changes.
