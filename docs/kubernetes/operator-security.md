# Kubernetes Operator: Security Architecture

The operator is designed with a "security-first" approach to manage LLM infrastructure safely.

## Secret Handling

- **No Raw Secrets:** The operator never accepts or stores raw API keys or passwords in Custom Resource specifications.
- **Secret References:** Sensitive data must be stored in standard Kubernetes `Secret` resources. The CRs reference these secrets by name (`apiKeySecretRef`).
- **Namespace Isolation:** The operator only looks for secrets within the same namespace as the CR, preventing cross-tenant secret leakage.

## Least Privilege (RBAC)

The operator should run with a dedicated ServiceAccount and limited RBAC permissions:
- **Custom Resources:** `get`, `list`, `watch`, `patch` (status) on `llm.stack.local` group.
- **Core Resources:** `create`, `update`, `patch`, `delete` on `deployments`, `services`, `configmaps`.
- **Secrets:** `get` only (to validate existence). It does not need `list` or `watch` on all secrets.

## Resource Isolation

- **Owner References:** All created resources have the parent CR as the owner. Deleting the CR automatically triggers a garbage collection of all sub-resources.
- **GPU Quotas:** The operator enforces GPU limits at the Pod level, preventing any single runtime from monopolizing cluster resources.

## Hardening

- **Dry-Run Mode:** Allows auditing of operator decisions before application.
- **Idempotency:** Prevents resource thrashing or duplicate creation during intermittent network issues.
