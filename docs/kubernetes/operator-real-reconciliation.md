---
owner: platform-ops
status: consolidated
---

# Kubernetes Operator: Real Reconciliation

The LLM Inference Stack operator has evolved from a simple logger to a real minimal reconciler. It manages the lifecycle of Custom Resources (CRs) by ensuring the desired state in Kubernetes matches the specification.

## Managed Resources

### LLMInferenceStack
- **Deployment:** Manages the control plane instances.
- **Service:** Exposes the control plane internally.
- **Status:** Tracks the readiness of the stack.

### LLMModelRuntime
- **Deployment:** Manages the model serving instances.
- **GPU Support:** Automatically configures NVIDIA GPU limits if specified in the CR.

### LLMProvider
- **Connectivity:** Validates that the referenced `apiKeySecretRef` exists in the same namespace.
- **Security:** Does not handle raw secrets; only references them via `SecretRef`.

### LLMTenant
- **Registration:** Records tenant metadata and quota configurations.

## Reconciliation Loop

The operator uses the [Kopf](https://kopf.readthedocs.io/) framework. Each reconciliation step is idempotent:
1. **Fetch Spec:** Read the desired state from the CR.
2. **Apply Sub-resources:** Create or update Deployments, Services, and ConfigMaps.
3. **Set Ownership:** Uses `ownerReferences` to ensure sub-resources are deleted when the parent CR is deleted.
4. **Update Status:** Reports progress and errors via `status.conditions`.

## Execution Modes

- `OPERATOR_MODE=real`: reconciles Deployments, Services, provider secret references, and status conditions against the Kubernetes API.
- `OPERATOR_MODE=mock`: validates reconciliation intent and status semantics without applying subresources.
- `OPERATOR_MODE=dry_run` or `OPERATOR_DRY_RUN=true`: logs the intended changes and skips API side effects.
