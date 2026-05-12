#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXIT_CODE=0

echo "=== Validate v1.6 Release Line Audit ==="
echo ""

# 1. Audit script exists and is executable
echo "1. Check audit script exists and is executable..."
if [ -f "scripts/audit-v1.6-release-line.sh" ]; then
    if [ -x "scripts/audit-v1.6-release-line.sh" ]; then
        echo -e "  ${GREEN}PASS${NC}: scripts/audit-v1.6-release-line.sh exists and is executable"
    else
        echo -e "  ${RED}FAIL${NC}: scripts/audit-v1.6-release-line.sh is not executable"
        EXIT_CODE=1
    fi
else
    echo -e "  ${RED}FAIL${NC}: scripts/audit-v1.6-release-line.sh does not exist"
    EXIT_CODE=1
fi

# 2. docs/V1_6_AUDIT_SUMMARY.md exists
echo "2. Check docs/V1_6_AUDIT_SUMMARY.md exists..."
if [ -f "docs/V1_6_AUDIT_SUMMARY.md" ]; then
    echo -e "  ${GREEN}PASS${NC}: docs/V1_6_AUDIT_SUMMARY.md exists"
else
    echo -e "  ${RED}FAIL${NC}: docs/V1_6_AUDIT_SUMMARY.md does not exist"
    EXIT_CODE=1
fi

# 3. All versions v1.6.0 to v1.6.6 appear in docs/V1_6_AUDIT_SUMMARY.md
echo "3. Check all v1.6.x versions appear in docs/V1_6_AUDIT_SUMMARY.md..."
REQUIRED_VERSIONS=(
    "v1.6.0-openai-compat"
    "v1.6.1-openai-compat"
    "v1.6.1-product-hardening"
    "v1.6.2-installer-polish"
    "v1.6.3-readiness-cleanup"
    "v1.6.4-customer-demo-pack"
    "v1.6.5-sales-ops"
    "v1.6.6-repo-cleanup"
)

if [ -f "docs/V1_6_AUDIT_SUMMARY.md" ]; then
    SUMMARY_CONTENT=$(cat "docs/V1_6_AUDIT_SUMMARY.md")
    for VER in "${REQUIRED_VERSIONS[@]}"; do
        if echo "${SUMMARY_CONTENT}" | grep -q "${VER}"; then
            echo -e "  ${GREEN}PASS${NC}: ${VER} found"
        else
            echo -e "  ${RED}FAIL${NC}: ${VER} not found in docs/V1_6_AUDIT_SUMMARY.md"
            EXIT_CODE=1
        fi
    done
fi

# 4. No .tar.gz appears in versioned release dirs
echo "4. Check no .tar.gz in versioned release dirs..."
TARBALLS=$(find releases/ -maxdepth 2 -name '*.tar.gz' 2>/dev/null || true)
if [ -z "${TARBALLS}" ]; then
    echo -e "  ${GREEN}PASS${NC}: No .tar.gz found in releases/"
else
    echo -e "  ${RED}FAIL${NC}: Found .tar.gz in releases/"
    echo "${TARBALLS}" | while IFS= read -r line; do
        echo "    ${line}"
    done
    EXIT_CODE=1
fi

# 5. No secrets in manifests/summaries
echo "5. Check secrets in release manifests/summaries..."
SECRET_FOUND=false
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"
    "ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"
    "JWT_SECRET=[a-zA-Z0-9._-]{12,}"
    "ghp_[a-zA-Z0-9]{36}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
)

SAFE_PATTERNS=(
    "__redacted__"
    "sk-demo-"
    "sk-local-example"
    "admin-token-123"
    "example"
    "changeme"
    "localhost"
)

while IFS= read -r -d '' FILE; do
    if [[ "${FILE}" =~ \.json$ ]] || [[ "${FILE}" =~ \.md$ ]]; then
        REL_PATH="${FILE#./}"
        for PAT in "${SECRET_PATTERNS[@]}"; do
            MATCHES=$(grep -Eon -- "${PAT}" "${FILE}" 2>/dev/null || true)
            if [ -n "${MATCHES}" ]; then
                SAFE=false
                for SAFE_PAT in "${SAFE_PATTERNS[@]}"; do
                    if echo "${MATCHES}" | grep -qE "${SAFE_PAT}"; then
                        SAFE=true
                        break
                    fi
                done
                if [ "${SAFE}" = false ]; then
                    echo -e "  ${RED}FAIL${NC}: Possible secret in ${REL_PATH}: $(echo "${MATCHES}" | head -3)"
                    SECRET_FOUND=true
                fi
            fi
        done
    fi
done < <(find releases/ -maxdepth 2 -type f \( -name 'release-manifest.json' -o -name 'summary.json' -o -name 'summary.md' -o -name 'bundle-manifest.json' \) -print0 2>/dev/null)

if [ "${SECRET_FOUND}" = false ]; then
    echo -e "  ${GREEN}PASS${NC}: No secrets found in release manifests/summaries"
fi

# 6. Check audit JSON report is valid JSON
echo "6. Check audit JSON report validity..."
LATEST_AUDIT=$(find artifacts/final-qa/v1.6-audit/ -maxdepth 1 -type d 2>/dev/null | sort | tail -1)
if [ -n "${LATEST_AUDIT}" ]; then
    AUDIT_JSON="${LATEST_AUDIT}/v1.6-audit.json"
    if [ -f "${AUDIT_JSON}" ]; then
        if python3 -c "import json; json.load(open('${AUDIT_JSON}'))" 2>/dev/null; then
            echo -e "  ${GREEN}PASS${NC}: ${AUDIT_JSON} is valid JSON"
        else
            echo -e "  ${RED}FAIL${NC}: ${AUDIT_JSON} is not valid JSON"
            EXIT_CODE=1
        fi
    else
        echo -e "  ${YELLOW}SKIP${NC}: No audit JSON found (run audit first)"
    fi
else
    echo -e "  ${YELLOW}SKIP${NC}: No audit directory found (run audit first)"
fi

echo ""
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo -e "${GREEN}All validation checks passed.${NC}"
else
    echo -e "${RED}Some validation checks failed.${NC}"
    echo "Review results above."
fi

exit "${EXIT_CODE}"
