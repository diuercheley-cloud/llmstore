#!/usr/bin/env bash
set -euo pipefail

# scripts/release-local-production.sh
# Orchestrates the release process for local-production.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# Load operator errors library
if [[ -f "${ROOT_DIR}/lib/operator-errors.sh" ]]; then
  source "${ROOT_DIR}/lib/operator-errors.sh"
fi

VERSION_ARG=""
ALLOW_DIRTY=false
SKIP_VALIDATION=false
INCLUDE_DOCS=false

usage() {
    echo "Usage: $0 --version <vX.Y.Z-local-production> [--allow-dirty] [--skip-validation] [--include-docs]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --version) VERSION_ARG="$2"; shift 2 ;;
        --allow-dirty) ALLOW_DIRTY=true; shift 1 ;;
        --skip-validation) SKIP_VALIDATION=true; shift 1 ;;
        --include-docs) INCLUDE_DOCS=true; shift 1 ;;
        *) usage ;;
    esac
done

if [[ -z "${VERSION_ARG}" ]]; then
    usage
fi

# Check git status
if [[ "${ALLOW_DIRTY}" == "false" ]]; then
    if ! git diff-index --quiet HEAD --; then
        operator_error "VALIDATION_FAILED" "O workspace do Git possui alterações não confirmadas." "Faça commit ou stash das suas alterações antes de realizar a release, ou use --allow-dirty."
        exit 1
    fi
fi

GIT_BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "unknown")"
LAST_TAG="$(git -C "${ROOT_DIR}" describe --tags --abbrev=0 --match "*-local-production" 2>/dev/null || echo "none")"

echo "Releasing version: ${VERSION_ARG}"
echo "Branch: ${GIT_BRANCH}"
echo "Commit: ${GIT_COMMIT}"
echo "Last local-production tag: ${LAST_TAG}"

# Detect LOCAL_APPLIANCE_MODE from .env.local
LOCAL_APPLIANCE_MODE=$(grep "^LOCAL_APPLIANCE_MODE=" .env.local 2>/dev/null | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "false")

if [[ "${LOCAL_APPLIANCE_MODE}" == "true" ]]; then
    echo "LOCAL_APPLIANCE_MODE detected. Enforcing security guards..."
    
    echo "Running secrets scan..."
    if ! "${SCRIPT_DIR}/check-secrets.sh" --all; then
        operator_error "SECRET_DETECTED" "A varredura de segredos encontrou problemas." "Remova todos os segredos antes de realizar a release para garantir a segurança."
        exit 1
    fi

    echo "Validating production readiness..."
    if ! "${SCRIPT_DIR}/production-readiness-local.sh"; then
        operator_warning "READY_DEGRADED" "O teste de prontidão de produção (readiness) falhou ou tem avisos." "Revise o relatório de readiness antes de prosseguir com a release."
    fi
fi

VALIDATION_RESULT="skipped"
if [[ "${SKIP_VALIDATION}" == "false" ]]; then
    echo "Running validation..."
    # We don't use 'set -e' for the validation script to allow manifest generation on failure
    if VALIDATION_VERSION="${VERSION_ARG}" "${SCRIPT_DIR}/validate-local-production-full.sh"; then
        VALIDATION_RESULT="success"
    else
        VALIDATION_RESULT="failure"
        echo "Validation failed!"
    fi
fi

# Find most recent artifact
LATEST_ARTIFACT_DIR="$(ls -td "${ROOT_DIR}/artifacts/local-production-validation"/*/ 2>/dev/null | head -n 1 | sed 's/\/$//' || echo "")"

if [[ -z "${LATEST_ARTIFACT_DIR}" && "${SKIP_VALIDATION}" == "false" ]]; then
    echo "Warning: No validation artifacts found."
fi

RELEASE_DIR="${ROOT_DIR}/releases/${VERSION_ARG}"
mkdir -p "${RELEASE_DIR}"

if [[ -n "${LATEST_ARTIFACT_DIR}" && -d "${LATEST_ARTIFACT_DIR}" ]]; then
    echo "Copying artifacts from ${LATEST_ARTIFACT_DIR}..."
    cp "${LATEST_ARTIFACT_DIR}/summary.md" "${RELEASE_DIR}/" 2>/dev/null || echo "Warning: summary.md not found"
    cp "${LATEST_ARTIFACT_DIR}/summary.json" "${RELEASE_DIR}/" 2>/dev/null || echo "Warning: summary.json not found"
fi

if [[ "${INCLUDE_DOCS}" == "true" ]]; then
    echo "Copying docs..."
    cp "${ROOT_DIR}/docs/LOCAL_PRODUCTION_VALIDATION.md" "${RELEASE_DIR}/" 2>/dev/null || echo "Warning: LOCAL_PRODUCTION_VALIDATION.md not found"
    if [[ -f "${ROOT_DIR}/docs/LOCAL_PRODUCTION_RUNBOOK.md" ]]; then
        cp "${ROOT_DIR}/docs/LOCAL_PRODUCTION_RUNBOOK.md" "${RELEASE_DIR}/"
    fi
fi

# Generate manifest
"${SCRIPT_DIR}/generate-release-manifest.sh" \
    --version "${VERSION_ARG}" \
    --artifact-dir "${LATEST_ARTIFACT_DIR:-none}" \
    --validation-result "${VALIDATION_RESULT}"

if [[ "${VALIDATION_RESULT}" == "success" && -x "${SCRIPT_DIR}/validate-release-metadata.sh" ]]; then
    "${SCRIPT_DIR}/validate-release-metadata.sh" \
        --version "${VERSION_ARG}" \
        --release-dir "${RELEASE_DIR}"
fi

echo "Redacting sensitive information from release artifacts..."
"${SCRIPT_DIR}/redact-local-sensitive-artifacts.sh" --path "${RELEASE_DIR}" --in-place

echo "Validating release artifacts security..."
if ! "${SCRIPT_DIR}/validate-release-artifacts-security.sh" --release-dir "${RELEASE_DIR}"; then
    operator_error "SECURITY_FAILED" "A validação de segurança dos artefatos de release falhou!" "Corrija as falhas de segurança apontadas nos artefatos em ${RELEASE_DIR}."
    exit 1
fi

echo "--------------------------------------------------"
operator_success "Release ${VERSION_ARG} preparada com sucesso em ${RELEASE_DIR}"

add_next_step "git add releases/${VERSION_ARG}"
add_next_step "git commit -m \"chore: release ${VERSION_ARG}\""
add_next_step "git tag ${VERSION_ARG}"
add_next_step "git push origin ${GIT_BRANCH}"
add_next_step "git push origin ${VERSION_ARG}"

print_next_steps
