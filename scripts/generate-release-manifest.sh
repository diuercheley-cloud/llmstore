#!/usr/bin/env bash
set -euo pipefail

# scripts/generate-release-manifest.sh
# Generates a release-manifest.json for a specific version.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

VERSION=""
ARTIFACT_DIR=""
VALIDATION_RESULT="unknown"

usage() {
    echo "Usage: $0 --version <vX.Y.Z> --artifact-dir <path> [--validation-result <success|failure>]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --version) VERSION="$2"; shift 2 ;;
        --artifact-dir) ARTIFACT_DIR="$2"; shift 2 ;;
        --validation-result) VALIDATION_RESULT="$2"; shift 2 ;;
        *) usage ;;
    esac
done

if [[ -z "${VERSION}" || -z "${ARTIFACT_DIR}" ]]; then
    usage
fi

RELEASE_DIR="${ROOT_DIR}/releases/${VERSION}"
MANIFEST_PATH="${RELEASE_DIR}/release-manifest.json"

mkdir -p "${RELEASE_DIR}"

GIT_BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_TAGS="$(git -C "${ROOT_DIR}" tag --points-at HEAD 2>/dev/null | tr '\n' ',' | sed 's/,$//' || echo "")"
GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Detect files
DOCS_COUNT=$(find "${ROOT_DIR}/docs" -maxdepth 1 -name "*.md" | wc -l)
SCRIPTS_COUNT=$(find "${ROOT_DIR}/scripts" -maxdepth 1 -name "*.sh" | wc -l)
COMPOSE_FILES=$(find "${ROOT_DIR}" -maxdepth 1 -name "docker-compose*.yml" -printf "%f," | sed 's/,$//')
ENV_EXAMPLES=$(find "${ROOT_DIR}" -maxdepth 1 -name ".env.example*" -printf "%f," | sed 's/,$//')

# Known limitations (can be expanded)
KNOWN_LIMITATIONS="Local production hardening phase. No real PSP integration. Requires Docker."

python3 - <<PY
import json
import os

manifest = {
    "release_name": "llm-inference-stack-local-production",
    "version": "${VERSION}",
    "git_branch": "${GIT_BRANCH}",
    "git_commit": "${GIT_COMMIT}",
    "git_tags_pointing_to_commit": "${GIT_TAGS}".split(",") if "${GIT_TAGS}" else [],
    "generated_at": "${GENERATED_AT}",
    "validation_artifact_path": "${ARTIFACT_DIR}",
    "summary_json_path": "summary.json",
    "summary_md_path": "summary.md",
    "docs_included_count": ${DOCS_COUNT},
    "scripts_included_count": ${SCRIPTS_COUNT},
    "docker_compose_files": "${COMPOSE_FILES}".split(",") if "${COMPOSE_FILES}" else [],
    "important_env_example_files": "${ENV_EXAMPLES}".split(",") if "${ENV_EXAMPLES}" else [],
    "models_included": False,
    "rag_uploads_included": False,
    "psp_integration": False,
    "pix_real_billing": False,
    "localhost_mode": True,
    "known_limitations": "${KNOWN_LIMITATIONS}",
    "validation_result": "${VALIDATION_RESULT}"
}

with open("${MANIFEST_PATH}", "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")

print(f"Manifest generated at: ${MANIFEST_PATH}")
PY
