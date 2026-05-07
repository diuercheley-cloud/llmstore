#!/usr/bin/env bash
set -euo pipefail

# scripts/release-local-production.sh
# Orchestrates the release process for local-production.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

VERSION=""
ALLOW_DIRTY=false
SKIP_VALIDATION=false
INCLUDE_DOCS=false

usage() {
    echo "Usage: $0 --version <vX.Y.Z-local-production> [--allow-dirty] [--skip-validation] [--include-docs]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --version) VERSION="$2"; shift 2 ;;
        --allow-dirty) ALLOW_DIRTY=true; shift 1 ;;
        --skip-validation) SKIP_VALIDATION=true; shift 1 ;;
        --include-docs) INCLUDE_DOCS=true; shift 1 ;;
        *) usage ;;
    esac
done

if [[ -z "${VERSION}" ]]; then
    usage
fi

# Check git status
if [[ "${ALLOW_DIRTY}" == "false" ]]; then
    if ! git diff-index --quiet HEAD --; then
        echo "Error: Git workspace is dirty. Use --allow-dirty to proceed anyway."
        exit 1
    fi
fi

GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
LAST_TAG="$(git describe --tags --abbrev=0 --match "*-local-production" 2>/dev/null || echo "none")"

echo "Releasing version: ${VERSION}"
echo "Branch: ${GIT_BRANCH}"
echo "Commit: ${GIT_COMMIT}"
echo "Last local-production tag: ${LAST_TAG}"

VALIDATION_RESULT="skipped"
if [[ "${SKIP_VALIDATION}" == "false" ]]; then
    echo "Running validation..."
    # We don't use 'set -e' for the validation script to allow manifest generation on failure
    if "${SCRIPT_DIR}/validate-local-production-full.sh"; then
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

RELEASE_DIR="${ROOT_DIR}/releases/${VERSION}"
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
    --version "${VERSION}" \
    --artifact-dir "${LATEST_ARTIFACT_DIR:-none}" \
    --validation-result "${VALIDATION_RESULT}"

echo "--------------------------------------------------"
echo "Release ${VERSION} prepared in ${RELEASE_DIR}"
ls -l "${RELEASE_DIR}"
echo "--------------------------------------------------"
echo "Next suggested commands:"
echo "  git add releases/${VERSION}"
echo "  git commit -m \"chore: release ${VERSION}\""
echo "  git tag ${VERSION}"
echo "  git push origin ${GIT_BRANCH}"
echo "  git push origin ${VERSION}"
