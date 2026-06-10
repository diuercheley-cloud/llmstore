#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/deploy-summary.md"
NAMESPACE="${K8S_NAMESPACE:-llm-stack}"
HELM_RELEASE="${HELM_RELEASE:-llm-stack-release}"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Deployment Summary - ${TIMESTAMP}" > "${REPORT_FILE}"
log_report "## Deployment Mode: Kubernetes"

# 1. Renderizar Helm chart
log_report "### Rendering Helm Chart"
mkdir -p "${ROOT_DIR}/deploy/rendered"
helm template "${HELM_RELEASE}" "${ROOT_DIR}/deploy/helm/llm-inference-stack" \
    --namespace "${NAMESPACE}" \
    > "${ROOT_DIR}/deploy/rendered/manifests.yaml"
log_report "- [x] Helm templates rendered to deploy/rendered/manifests.yaml"

# 2. Validar manifests
log_report "### Validating Manifests"
if command -v kubeconform >/dev/null 2>&1; then
    kubeconform -summary "${ROOT_DIR}/deploy/rendered/manifests.yaml" | tee -a "${REPORT_FILE}"
else
    kubectl apply --dry-run=client -f "${ROOT_DIR}/deploy/rendered/manifests.yaml" >/dev/null
    log_report "- [x] Manifests validated (kubectl dry-run)"
fi

# 3. Aplicar namespace
log_report "### Applying Namespace"
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
log_report "- [x] Namespace ${NAMESPACE} ensured"

# 4. Aplicar secrets por referência (Instruction: Do not create real secrets in git)
log_report "### Secret Reference Validation"
# Check if required secrets exist in k8s
for secret in db-credentials redis-credentials admin-tokens; do
    if kubectl get secret "${secret}" -n "${NAMESPACE}" >/dev/null 2>&1; then
        log_report "- [x] Secret found: ${secret}"
    else
        log_report "- [ ] Secret MISSING: ${secret} (Must be created manually or via Vault)"
        # Note: We don't fail here if it's a dry-run or if we expect them to be injected later, 
        # but for a real deploy we might want to exit.
    fi
done

# 5. Aplicar e aguardar deployments
log_report "### Applying to Cluster"
kubectl apply -f "${ROOT_DIR}/deploy/rendered/manifests.yaml" -n "${NAMESPACE}"

log_report "### Waiting for Deployments"
kubectl rollout status deployment/control-plane -n "${NAMESPACE}" --timeout=300s | tee -a "${REPORT_FILE}"
kubectl rollout status deployment/frontend-admin -n "${NAMESPACE}" --timeout=300s | tee -a "${REPORT_FILE}"

# 6. Executar k8s readiness
log_report "### K8s Readiness Check"
# Quick check of pod status
kubectl get pods -n "${NAMESPACE}" | tee -a "${REPORT_FILE}"

log_report "## Result"
log_report "**K8S DEPLOYMENT INITIATED**"

echo "Artifact generated at: ${REPORT_FILE}"
