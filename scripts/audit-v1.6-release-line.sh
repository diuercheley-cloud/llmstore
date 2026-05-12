#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
AUDIT_DIR="artifacts/final-qa/v1.6-audit/${TIMESTAMP}"
mkdir -p "${AUDIT_DIR}"

AUDIT_JSON="${AUDIT_DIR}/v1.6-audit.json"
AUDIT_MD="${AUDIT_DIR}/v1.6-audit.md"
HELPER_PY="scripts/audit_v1_6_helper.py"

VERSIONS=(
    "v1.6.0-openai-compat"
    "v1.6.1-openai-compat"
    "v1.6.1-product-hardening"
    "v1.6.2-installer-polish"
    "v1.6.3-readiness-cleanup"
    "v1.6.4-customer-demo-pack"
    "v1.6.5-sales-ops"
    "v1.6.6-repo-cleanup"
)

VERSION_OBJECTIVES=(
    "OpenAI-compatible responses e embeddings APIs"
    "Ajuste na versao e correcoes na API e interface do Admin Lab (tag obsoleta, substituida por v1.6.1-product-hardening)"
    "Makefile, system control center, migrations hardening, multi-tenant, abuse protection"
    "Instalador local, wizard, checklist, backup/upgrade, validacao pos-instalacao"
    "Readiness final com correcao de warnings, probe chat/SSE/TTS/CORS"
    "Demo pack comercial com 5 cenarios, meeting ready check, capabilities page"
    "Fluxos comerciais: CRM, propostas, orcamentos, contratos, white-label"
    "Repo cleanup: consolidacao do layout, padronizacao shell, historico de releases"
)

REQUIRED_RELEASE_FILES=(
    "release-manifest.json"
    "summary.json"
    "summary.md"
    "bundle-manifest.json"
    "bundle-checksums.sha256"
)

# ---------- helpers ----------

resolve_commit() {
    git rev-parse "${1}^{commit}" 2>/dev/null || echo "UNRESOLVED"
}

branch_exists() {
    git rev-parse --verify "$1" 1>/dev/null 2>&1
}

branch_commit() {
    git rev-parse "${1}^{commit}" 2>/dev/null || echo ""
}

detect_tar_gz() {
    local dir="$1"
    local found
    found=$(find "${dir}" -maxdepth 1 -name '*.tar.gz' 2>/dev/null | head -5)
    [ -n "${found}" ] && echo "yes" || echo "no"
}

# ---------- main ----------

> "${AUDIT_DIR}/.results.json"

echo "=== Auditoria v1.6.x Release Line ==="
echo "Timestamp: ${TIMESTAMP}"
echo ""

for i in "${!VERSIONS[@]}"; do
    TAG="${VERSIONS[$i]}"
    OBJECTIVE="${VERSION_OBJECTIVES[$i]}"
    REL_DIR="releases/${TAG}"

    echo "--- Auditing ${TAG} ---"

    # Get tag commit
    TAG_COMMIT=$(resolve_commit "${TAG}")

    # Stable branch
    if branch_exists "stable/${TAG}"; then
        STABLE_BRANCH="stable/${TAG}"
        STABLE_COMMIT=$(branch_commit "stable/${TAG}")
    else
        STABLE_BRANCH=""
        STABLE_COMMIT=""
    fi

    # Feature branch
    if branch_exists "feature/${TAG}"; then
        FEATURE_BRANCH="feature/${TAG}"
        FEATURE_COMMIT=$(branch_commit "feature/${TAG}")
    else
        FEATURE_BRANCH=""
        FEATURE_COMMIT=""
    fi

    # Tag/stable consistency
    if [ -n "${STABLE_BRANCH}" ] && [ -n "${STABLE_COMMIT}" ]; then
        if [ "${TAG_COMMIT}" = "${STABLE_COMMIT}" ]; then
            TAG_STABLE_CONSISTENT="yes"
        else
            TAG_STABLE_CONSISTENT="no"
        fi
    elif [ -z "${STABLE_BRANCH}" ]; then
        TAG_STABLE_CONSISTENT="no_stable_branch"
    else
        TAG_STABLE_CONSISTENT="unknown"
    fi

    # Feature consistency
    if [ -n "${FEATURE_BRANCH}" ] && [ -n "${FEATURE_COMMIT}" ]; then
        if [ "${TAG_COMMIT}" = "${FEATURE_COMMIT}" ]; then
            FEATURE_CONSISTENT="yes"
        else
            FEATURE_CONSISTENT="no"
        fi
    else
        FEATURE_CONSISTENT="no_feature_branch"
    fi

    # Release dir
    if [ -d "${REL_DIR}" ]; then
        REL_EXISTS="yes"
        RELEASE_FILES="{}"
        for RF in "${REQUIRED_RELEASE_FILES[@]}"; do
            if [ -f "${REL_DIR}/${RF}" ]; then
                RELEASE_FILES=$(echo "${RELEASE_FILES}" | python3 -c "
import json,sys
d = json.load(sys.stdin)
d['${RF}'] = 'present'
print(json.dumps(d))
" 2>/dev/null)
            else
                RELEASE_FILES=$(echo "${RELEASE_FILES}" | python3 -c "
import json,sys
d = json.load(sys.stdin)
d['${RF}'] = 'missing'
print(json.dumps(d))
" 2>/dev/null)
            fi
        done

        TAR_GZ=$(detect_tar_gz "${REL_DIR}")

        # Check secrets using Python script
        SECRETS_JSON=$(python3 "${HELPER_PY}" check_secrets "${REL_DIR}" 2>/dev/null || echo '{"found":"error","details":""}')

        # Check manifest commit using Python script
        MANIFEST_COMMIT_CHECK=$(python3 "${HELPER_PY}" check_manifest_commit "${REL_DIR}" "${TAG_COMMIT}" 2>/dev/null || echo "unknown")

        # Check git_tags_pointing_to_commit
        if [ $i -gt 0 ]; then
            PREV_TAG="${VERSIONS[$((i-1))]}"
        else
            PREV_TAG=""
        fi
        GIT_TAGS_CHECK=$(python3 "${HELPER_PY}" check_git_tags "${REL_DIR}" "${PREV_TAG}" 2>/dev/null || echo "unknown")
    else
        REL_EXISTS="no"
        RELEASE_FILES="{}"
        TAR_GZ="n/a"
        SECRETS_JSON='{"found":"n/a","details":""}'
        MANIFEST_COMMIT_CHECK="n/a"
        GIT_TAGS_CHECK="n/a"
    fi

    # CHANGELOG
    if grep -q "${TAG}" CHANGELOG.md 2>/dev/null; then
        CHANGELOG_EXISTS="yes"
    elif [ "${TAG}" = "v1.6.0-openai-compat" ] && grep -q "v1.6.0-beta.1" CHANGELOG.md 2>/dev/null; then
        CHANGELOG_EXISTS="partial (listed as v1.6.0-beta.1)"
    else
        CHANGELOG_EXISTS="no"
    fi

    # VERSION at tag
    VERSION_AT_TAG=$(git show "${TAG}:VERSION" 2>/dev/null || echo "unknown")

    # RELEASE_HISTORY
    if grep -q "${TAG}" docs/RELEASE_HISTORY.md 2>/dev/null; then
        RELEASE_HISTORY_STATUS="present"
    else
        RELEASE_HISTORY_STATUS="missing"
    fi

    # Write result line
    python3 "${HELPER_PY}" emit_result \
        "${TAG}" "${OBJECTIVE}" "${TAG_COMMIT}" "${STABLE_BRANCH}" "${STABLE_COMMIT}" \
        "${FEATURE_BRANCH}" "${FEATURE_COMMIT}" "${TAG_STABLE_CONSISTENT}" "${FEATURE_CONSISTENT}" \
        "${REL_EXISTS}" "${RELEASE_FILES}" "${TAR_GZ}" "${SECRETS_JSON}" \
        "${MANIFEST_COMMIT_CHECK}" "${GIT_TAGS_CHECK}" "${CHANGELOG_EXISTS}" \
        "${VERSION_AT_TAG}" "${RELEASE_HISTORY_STATUS}" \
        "${AUDIT_DIR}/.results.json" 2>/dev/null

    echo "  Tag commit: ${TAG_COMMIT:0:12}"
    echo "  Stable branch: ${STABLE_BRANCH:-NONE} -> commit: ${STABLE_COMMIT:0:12}"
    echo "  Feature branch: ${FEATURE_BRANCH:-NONE}"
    echo "  Tag/stable consistent: ${TAG_STABLE_CONSISTENT}"
    echo "  Feature consistent: ${FEATURE_CONSISTENT}"
    echo "  Release dir exists: ${REL_EXISTS}"
    echo "  Manifest commit check: ${MANIFEST_COMMIT_CHECK}"
    echo ""
done

# ---------- generate final JSON and MD ----------

python3 "${HELPER_PY}" generate_report "${AUDIT_DIR}" "${TIMESTAMP}" 2>&1

echo ""
echo "=== Auditoria concluida ==="
echo "JSON: ${AUDIT_JSON}"
echo "MD:   ${AUDIT_MD}"

# Print inconsistencies
echo ""
echo "=== Inconsistencias Encontradas ==="
python3 "${HELPER_PY}" print_inconsistencies "${AUDIT_JSON}" 2>&1

:
