#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
PASS=0
FAIL=0

BASE_URL="${BASE_URL:-$(default_base_url)}"

pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}[FAIL]${NC} $1"; }

echo "============================================================"
echo "  VALIDATE - Capabilities Page"
echo "============================================================"
echo ""

# 1. HTML page exists
echo -e "\n--- Test 1: HTML page file exists ---"
HTML_FILE="${ROOT_DIR}/control_plane/app/static/www/capabilities.html"
if [[ -f "$HTML_FILE" ]]; then
  pass "capabilities.html exists"
else
  fail "capabilities.html not found"
fi

# 2. Route handler exists in public.py
echo -e "\n--- Test 2: Route handler in public.py ---"
PUBLIC_PY="${ROOT_DIR}/control_plane/app/api/public.py"
if grep -q "def capabilities_page" "$PUBLIC_PY"; then
  pass "/capabilities route handler found"
else
  fail "/capabilities route handler missing"
fi

if grep -q "def public_capabilities" "$PUBLIC_PY"; then
  pass "/public/capabilities route handler found"
else
  fail "/public/capabilities route handler missing"
fi

# 3. Landing page has capabilities link
echo -e "\n--- Test 3: Landing page links to capabilities ---"
INDEX_HTML="${ROOT_DIR}/control_plane/app/static/www/index.html"
if grep -q "/capabilities" "$INDEX_HTML"; then
  pass "Landing page links to /capabilities"
else
  fail "Landing page missing /capabilities link"
fi

# 4. Page contains expected features
echo -e "\n--- Test 4: Features listed in HTML ---"
for feature in "OpenAI-compatible" "Chat Completions" "Streaming" "Models" "Embeddings" "Responses" "RAG" "TTS" "Client Portal" "Admin Dashboard" "Admin Lab" "Billing" "Security Report" "Production Readiness" "Backup" "Upgrade" "Demo Pack"; do
  if grep -qi "$feature" "$HTML_FILE"; then
    pass "Feature found: $feature"
  else
    fail "Feature missing: $feature"
  fi
done

# 5. Page contains limitations
echo -e "\n--- Test 5: Limitations in HTML ---"
for limit in "PSP" "PIX" "Tools / Function Calling" "hardware local" "HTTPS" "seguranca absoluta"; do
  if grep -qi "$limit" "$HTML_FILE"; then
    pass "Limitation found: $limit"
  else
    fail "Limitation missing: $limit"
  fi
done

# 6. No local paths exposed
echo -e "\n--- Test 6: No sensitive local paths ---"
for bad in "/home/" "/root/" "/var/" "/etc/" "/models/" "/data/"; do
  if grep -q "$bad" "$HTML_FILE"; then
    fail "Sensitive path exposed: $bad"
  else
    pass "No sensitive path: $bad"
  fi
done

# 7. No secrets in HTML
echo -e "\n--- Test 7: No secrets in HTML ---"
for pattern in "ADMIN_TOKEN" "sk-[a-zA-Z0-9]" "Bearer " "-----BEGIN"; do
  if grep -q "$pattern" "$HTML_FILE" 2>/dev/null; then
    fail "Potential secret pattern found: $pattern"
  else
    pass "No secret pattern: $pattern"
  fi
done

# 8. JSON endpoint does not expose secrets
echo -e "\n--- Test 8: JSON route does not expose secrets ---"
if grep -q "Sem secrets" "$PUBLIC_PY"; then
  pass "JSON endpoint has no-secrets note"
else
  fail "JSON endpoint missing no-secrets note"
fi

if grep -q "limitations" "$PUBLIC_PY" && grep -q "features" "$PUBLIC_PY"; then
  pass "JSON endpoint has features and limitations"
else
  fail "JSON endpoint missing features or limitations"
fi

# 9. Validate version tag in HTML
echo -e "\n--- Test 9: Version loading via JS ---"
if grep -q "version" "$HTML_FILE"; then
  pass "Version displayed on page"
else
  fail "Version not displayed"
fi

# 10. Validate styling and structure
echo -e "\n--- Test 10: Basic HTML structure ---"
if grep -q "<!doctype html>" "$HTML_FILE" && grep -q "</html>" "$HTML_FILE"; then
  pass "Valid HTML structure"
else
  fail "Invalid HTML structure"
fi

if grep -q "cap-status" "$HTML_FILE"; then
  pass "Status CSS classes present"
else
  fail "Status CSS classes missing"
fi

if grep -q "limits-box" "$HTML_FILE"; then
  pass "Limitations box present"
else
  fail "Limitations box missing"
fi

echo ""
echo "============================================================"
echo "  VALIDATION COMPLETE"
echo "============================================================"
echo "  Passed: ${PASS}"
echo "  Failed: ${FAIL}"
echo "============================================================"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
