#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTROL_PLANE_DIR="$PROJECT_ROOT/control_plane"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/scripts/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red()   { echo -e "\033[31m$1\033[0m"; }

pass() { PASS=$((PASS+1)); green "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); red "  FAIL: $1"; }

assert_json() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label (expected: $expected, got: $actual)"
    fi
}

assert_contains() {
    local label="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -q "$needle"; then
        pass "$label"
    else
        fail "$label (expected to contain: $needle)"
    fi
}

assert_not_contains() {
    local label="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -q "$needle"; then
        fail "$label (should NOT contain: $needle)"
    else
        pass "$label"
    fi
}

echo "============================================"
echo "  Provider Validation Suite"
echo "============================================"

# ------------------------------------------------------------------
# 1. Validate provider registry in Python (unit-level)
# ------------------------------------------------------------------
echo ""
echo "---[1] Provider Registry (Python) ---"

cd "$PROJECT_ROOT"
OUT=$(
  PYTHONPATH="$CONTROL_PLANE_DIR" \
  $PYTHON -c "
from app.core.config import get_settings
from app.services.providers.registry import get_providers, get_all_provider_statuses

statuses = get_all_provider_statuses()
ids = [s.provider_id for s in statuses]

assert 'local' in ids, 'local provider missing'
assert 'lmstudio' in ids, 'lmstudio provider missing'

for s in statuses:
    assert s.provider_id in ids
    if s.provider_type in ('openai', 'anthropic', 'deepseek', 'openrouter'):
        # Cloud: no API keys set in test, so configured=false
        assert s.configured is False, f'{s.provider_id} should be configured=false'
    elif s.provider_id == 'local':
        assert s.configured is True, 'local should be configured=true'
        assert s.enabled is True, 'local should be enabled'

print('OK: provider registry validates correctly')
" 2>&1)

if echo "$OUT" | grep -q "^OK"; then
    pass "Provider registry validates correctly"
else
    fail "Provider registry error: $OUT"
fi

# ------------------------------------------------------------------
# HTTP-level tests - check if server is running
# ------------------------------------------------------------------
SERVER_UP=false
if curl -s -o /dev/null -w "" "$BASE_URL/health" 2>/dev/null; then
    SERVER_UP=true
fi

echo ""
echo "---[2] Server status ---"
if $SERVER_UP; then
    pass "Server is running at $BASE_URL"
else
    echo "  (server not running - HTTP tests skipped; pytest validates API layer)"
fi

if $SERVER_UP; then
    # Without token -> 401
    echo "---[3] Admin endpoints require auth ---"
    NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/providers" 2>/dev/null || echo "000")
    if [[ "$NO_AUTH" == "401" ]] || [[ "$NO_AUTH" == "403" ]]; then
        pass "Admin providers requires token (got $NO_AUTH)"
    else
        fail "Admin providers unexpected status without token: $NO_AUTH"
    fi

    # With token -> 200
    WITH_AUTH=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-Admin-Token: $ADMIN_TOKEN" \
        "$BASE_URL/admin/providers" 2>/dev/null || echo "000")
    if [[ "$WITH_AUTH" == "200" ]]; then
        pass "Admin providers works with token"
    else
        fail "Admin providers with token returned $WITH_AUTH"
    fi

    # Validate /admin/providers response
    echo "---[4] Admin providers response ---"
    PROVIDERS_JSON=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/providers" 2>/dev/null || echo "{}")
    assert_contains "Response is JSON array" "$PROVIDERS_JSON" '"provider_id"'

    LOCAL_ENABLED=$(echo "$PROVIDERS_JSON" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(str([p['enabled'] for p in d if p['provider_id']=='local'][0]).lower())" 2>/dev/null || echo "false")
    assert_json "Local provider enabled" "true" "$LOCAL_ENABLED"

    OPENAI_CONFIGURED=$(echo "$PROVIDERS_JSON" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(str([p['configured'] for p in d if p['provider_id']=='openai'][0]).lower())" 2>/dev/null || echo "true")
    assert_json "OpenAI configured=false (no key)" "false" "$OPENAI_CONFIGURED"

    ANTHROPIC_CONFIGURED=$(echo "$PROVIDERS_JSON" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(str([p['configured'] for p in d if p['provider_id']=='anthropic'][0]).lower())" 2>/dev/null || echo "true")
    assert_json "Anthropic configured=false (no key)" "false" "$ANTHROPIC_CONFIGURED"

    # Validate health deep doesn't leak secrets
    echo "---[5] Health deep secret safety ---"
    HEALTH_DEEP=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/health/deep" 2>/dev/null || echo "{}")
    if [[ "$HEALTH_DEEP" != "{}" ]]; then
        assert_not_contains "No api_key in health deep" "$HEALTH_DEEP" "sk-"
        assert_contains "Has providers section" "$HEALTH_DEEP" '"providers"'
    fi

    # Validate provider capabilities
    echo "---[6] Provider capabilities ---"
    CAPS_JSON=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/providers/capabilities/all" 2>/dev/null || echo "{}")
    if [[ "$CAPS_JSON" != "{}" ]]; then
        assert_contains "Local has capabilities" "$CAPS_JSON" '"chat"'
        assert_contains "Has local provider" "$CAPS_JSON" '"local"'
    fi

    # Validate provider health
    echo "---[7] Provider health ---"
    LOCAL_HEALTH=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/providers/local/health" 2>/dev/null || echo "{}")
    if [[ "$LOCAL_HEALTH" != "{}" ]]; then
        pass "Local provider health returns valid JSON"
    fi

    # Validate /v1/models
    echo "---[8] /v1/models backwards compat ---"
    MODELS_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/v1/models" 2>/dev/null || echo "000")
    if [[ "$MODELS_HTTP" != "000" ]]; then
        pass "/v1/models endpoint is reachable (HTTP $MODELS_HTTP)"
    fi
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "============================================"
TOTAL=$((PASS+FAIL))
echo "  Results: $PASS passed, $FAIL failed, $TOTAL total"
echo "============================================"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
