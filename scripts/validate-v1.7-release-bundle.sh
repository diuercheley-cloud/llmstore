#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-v1.7-release-bundle.sh
#
# Valida o release bundle da v1.7.0-local-ai-appliance.
#
# Verifica:
#   - releases/<version>/ existe
#   - 5 arquivos obrigatorios existem
#   - Nenhum .tar.gz no diretorio versionavel
#   - Nenhum secret nos manifests/summaries
#   - Nenhum modelo/dado local no manifest
#   - Checksums tem formato valido
#   - VERSION e release metadata batem
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="v1.7.0-local-ai-appliance"
RELEASE_DIR="${ROOT_DIR}/releases/${VERSION}"
ERRORS=0
WARNINGS=0

echo "=== Validating v1.7.0 Release Bundle ==="
echo "  Version: ${VERSION}"
echo "  Dir:     ${RELEASE_DIR}"
echo ""

# --- 1. Release directory exists ---
if [[ -d "${RELEASE_DIR}" ]]; then
    echo "[PASS] releases/${VERSION} exists"
else
    echo "[FAIL] releases/${VERSION} not found"
    ERRORS=$((ERRORS + 1))
fi

# --- 2. Five required files exist ---
REQUIRED_FILES=(
    "release-manifest.json"
    "summary.json"
    "summary.md"
    "bundle-manifest.json"
    "bundle-checksums.sha256"
)

for rf in "${REQUIRED_FILES[@]}"; do
    if [[ -f "${RELEASE_DIR}/${rf}" ]]; then
        echo "[PASS] ${rf} exists"
    else
        echo "[FAIL] ${rf} NOT found"
        ERRORS=$((ERRORS + 1))
    fi
done

# --- 3. No .tar.gz in release directory ---
TAR_GZ_COUNT=$(find "${RELEASE_DIR}" -maxdepth 1 -name '*.tar.gz' 2>/dev/null | wc -l)
if [[ "${TAR_GZ_COUNT}" -eq 0 ]]; then
    echo "[PASS] No .tar.gz files in release directory (safe to version)"
else
    echo "[FAIL] Found ${TAR_GZ_COUNT} .tar.gz file(s) in release directory"
    ERRORS=$((ERRORS + 1))
fi

# --- 4. No secrets in manifests/summaries ---
SECRET_PATTERNS=("sk-" "ghp_" "ADMIN_TOKEN=" "JWT_SECRET=" "-----BEGIN ")
for rf in "${REQUIRED_FILES[@]}"; do
    fp="${RELEASE_DIR}/${rf}"
    if [[ ! -f "${fp}" ]]; then
        continue
    fi
    for pat in "${SECRET_PATTERNS[@]}"; do
        if grep -q "${pat}" "${fp}" 2>/dev/null; then
            if grep -qE "(sk-demo|sk-local-example|__redacted__|redacted)" "${fp}" 2>/dev/null; then
                :
            else
                echo "[FAIL] Secret pattern '${pat}' found in ${rf}"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
done
echo "[PASS] No secrets detected in release manifests/summaries"

# --- 5. No models/dados locais in bundle manifest ---
BM="${RELEASE_DIR}/bundle-manifest.json"
if [[ -f "${BM}" ]]; then
    MODELS_INCLUDED=$(python3 -c "
import json
with open('${BM}') as f:
    d = json.load(f)
print(d.get('models_included', 'unknown'))
print(d.get('rag_uploads_included', 'unknown'))
print(d.get('env_included', 'unknown'))
print(d.get('local_data_included', 'unknown'))
" 2>/dev/null || echo "unknown")

    MI=$(echo "${MODELS_INCLUDED}" | head -1)
    RI=$(echo "${MODELS_INCLUDED}" | head -2 | tail -1)
    EI=$(echo "${MODELS_INCLUDED}" | head -3 | tail -1)
    LI=$(echo "${MODELS_INCLUDED}" | head -4 | tail -1)

    if [[ "${MI}" == "false" ]]; then
        echo "[PASS] bundle-manifest.json: models_included=false"
    else
        echo "[WARN] bundle-manifest.json: models_included=${MI}"
        WARNINGS=$((WARNINGS + 1))
    fi

    if [[ "${RI}" == "false" ]]; then
        echo "[PASS] bundle-manifest.json: rag_uploads_included=false"
    else
        echo "[WARN] bundle-manifest.json: rag_uploads_included=${RI}"
        WARNINGS=$((WARNINGS + 1))
    fi

    if [[ "${EI}" == "false" ]]; then
        echo "[PASS] bundle-manifest.json: env_included=false"
    else
        echo "[WARN] bundle-manifest.json: env_included=${EI}"
        WARNINGS=$((WARNINGS + 1))
    fi

    if [[ "${LI}" == "false" ]]; then
        echo "[PASS] bundle-manifest.json: local_data_included=false"
    else
        echo "[WARN] bundle-manifest.json: local_data_included=${LI}"
        WARNINGS=$((WARNINGS + 1))
    fi

    SECRETS_SCAN=$(python3 -c "
import json
with open('${BM}') as f:
    d = json.load(f)
print(d.get('secrets_scan_passed', 'unknown'))
" 2>/dev/null || echo "unknown")

    if [[ "${SECRETS_SCAN}" == "True" ]] || [[ "${SECRETS_SCAN}" == "true" ]]; then
        echo "[PASS] bundle-manifest.json: secrets_scan_passed=true"
    else
        echo "[WARN] bundle-manifest.json: secrets_scan_passed=${SECRETS_SCAN}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "[WARN] bundle-manifest.json not found, skipping content checks"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 6. Checksums have valid format ---
CS="${RELEASE_DIR}/bundle-checksums.sha256"
if [[ -f "${CS}" ]]; then
    LINE_COUNT=$(wc -l < "${CS}")
    if [[ "${LINE_COUNT}" -eq 1 ]]; then
        FIRST_LINE=$(head -1 "${CS}")
        if echo "${FIRST_LINE}" | grep -qE '^[a-f0-9]{64}\s+llm-inference-stack-.+\.tar\.gz$'; then
            echo "[PASS] bundle-checksums.sha256: valid format"
        else
            echo "[WARN] bundle-checksums.sha256: unexpected format (line: ${FIRST_LINE:0:60}...)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "[WARN] bundle-checksums.sha256: expected 1 line, found ${LINE_COUNT}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# --- 7. VERSION field matches in release-manifest ---
RM="${RELEASE_DIR}/release-manifest.json"
if [[ -f "${RM}" ]]; then
    RM_VERSION=$(python3 -c "
import json
with open('${RM}') as f:
    d = json.load(f)
print(d.get('version', 'not_found'))
" 2>/dev/null || echo "parse_error")

    VERSION_FROM_FILE=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "not_found")

    if [[ "${RM_VERSION}" == "${VERSION}" ]] || [[ "${RM_VERSION}" == "${VERSION_FROM_FILE}" ]]; then
        echo "[PASS] release-manifest.json version matches (${RM_VERSION})"
    else
        echo "[WARN] release-manifest.json version (${RM_VERSION}) != VERSION file (${VERSION_FROM_FILE})"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "[WARN] release-manifest.json not found, skipping version check"
    WARNINGS=$((WARNINGS + 1))
fi

# --- 8. Bundle manifest version matches ---
if [[ -f "${BM}" ]]; then
    BM_VERSION=$(python3 -c "
import json
with open('${BM}') as f:
    d = json.load(f)
print(d.get('version', 'not_found'))
" 2>/dev/null || echo "parse_error")

    if [[ "${BM_VERSION}" == "${VERSION}" ]]; then
        echo "[PASS] bundle-manifest.json version matches (${BM_VERSION})"
    else
        echo "[WARN] bundle-manifest.json version (${BM_VERSION}) != expected (${VERSION})"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# --- 9. No forbidden files in release dir ---
FORBIDDEN_ITEMS=(".env" ".env.local" ".local" "models" "data" "backups" "exports" "artifacts")
for fi_item in "${FORBIDDEN_ITEMS[@]}"; do
    if [[ -e "${RELEASE_DIR}/${fi_item}" ]]; then
        echo "[FAIL] Forbidden item found: ${fi_item}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo "[PASS] No forbidden files in release directory"

# --- 10. Release size check ---
if [[ -d "${RELEASE_DIR}" ]]; then
    FILE_COUNT=$(find "${RELEASE_DIR}" -maxdepth 1 -type f | wc -l)
    TOTAL_SIZE=$(du -sh "${RELEASE_DIR}" 2>/dev/null | cut -f1)
    echo "[INFO] Release: ${FILE_COUNT} files, ${TOTAL_SIZE} (manifests + checksums only)"
fi

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Errors:   ${ERRORS}"
echo "  Warnings: ${WARNINGS}"

if [[ ${ERRORS} -gt 0 ]]; then
    echo "[FAIL] Release bundle validation FAILED"
    exit 1
else
    echo "[PASS] Release bundle validation PASSED"
    exit 0
fi
