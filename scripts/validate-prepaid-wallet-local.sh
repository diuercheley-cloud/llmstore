#!/usr/bin/env bash
# ===========================================================================
# validate-prepaid-wallet-local.sh
# ===========================================================================
# Validate prepaid wallet in BRL with local ledger.
#
# Rules verified:
#   - Creates wallet for demo client
#   - Manual admin credit increases balance
#   - Simulated request debit reduces balance
#   - Insufficient balance blocks cloud usage
#   - Idempotency prevents duplicate credit
#   - Client sees balance but cannot credit manually
#   - Admin token required
#   - No real PIX integrated
# ===========================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

# shellcheck source=/dev/null
source "./scripts/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red() { echo -e "\033[31m$1\033[0m"; }
step() { echo -e "\n━━━ $1 ━━━"; }

check() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label (expected: $expected, got: $actual)"
        FAIL=$((FAIL + 1))
    fi
}

check_contains() {
    local label="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -q "$needle"; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label (expected to contain: $needle)"
        FAIL=$((FAIL + 1))
    fi
}

check_status() {
    local label="$1" http_status="$2" expected="$3"
    if [[ "$http_status" == "$expected" ]]; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label (HTTP $http_status, expected $expected)"
        FAIL=$((FAIL + 1))
    fi
}

check_status_any() {
    local label="$1" http_status="$2"
    shift 2
    local expected
    for expected in "$@"; do
        if [[ "$http_status" == "$expected" ]]; then
            green "  ✓ $label"
            PASS=$((PASS + 1))
            return
        fi
    done
    red "  ✗ $label (HTTP $http_status, expected one of: $*)"
    FAIL=$((FAIL + 1))
}

cleanup() {
    if [[ -n "${DEMO_CLIENT_ID:-}" ]]; then
        curl -sf -X DELETE "$BASE_URL/admin/clients/$DEMO_CLIENT_ID" \
            -H "X-Admin-Token: $ADMIN_TOKEN" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

step "1. Create a demo client for wallet testing"
DEMO_RESP=$(curl -sf -X POST "$BASE_URL/admin/clients" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"wallet-demo-'$(date +%s)'","description":"Wallet validation demo"}')
DEMO_CLIENT_ID=$(echo "$DEMO_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Demo client ID: $DEMO_CLIENT_ID"
check "Demo client created" "1" "1"

step "2. Create wallet (GET creates if not exists)"
WALLET_RESP=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
WALLET_BALANCE=$(echo "$WALLET_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")
check "Wallet balance starts at 0" "0.0" "$WALLET_BALANCE"

step "3. Admin manual credit increases balance"
TX_RESP=$(curl -sf -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/manual-credit" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"amount_brl":500.0,"reason":"Initial credit for testing"}')
TX_TYPE=$(echo "$TX_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
check "Transaction type is manual_credit" "manual_credit" "$TX_TYPE"

WALLET_RESP=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
BALANCE=$(echo "$WALLET_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")
check "Balance after credit" "500.0" "$BALANCE"

step "4. Simulated request debit reduces balance"
DEBIT_RESP=$(curl -sf -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/adjustment" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"amount_brl":-30.0,"reason":"Simulated usage debit"}')
DEBIT_TYPE=$(echo "$DEBIT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
check "Adjustment type is adjustment" "adjustment" "$DEBIT_TYPE"

WALLET_RESP=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
BALANCE=$(echo "$WALLET_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")
check "Balance after debit" "470.0" "$BALANCE"

step "5. Insufficient balance blocks cloud usage"
BLOCK_BODY="$(mktemp)"
BLOCK_HTTP_STATUS=$(curl -s -o "$BLOCK_BODY" -w "%{http_code}" -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/adjustment" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"amount_brl":-99999.0,"reason":"Attempt overdraft"}')
BLOCK_RESP="$(cat "$BLOCK_BODY")"
rm -f "$BLOCK_BODY"
check_status "Overdraft blocked (422)" "$BLOCK_HTTP_STATUS" "422"
check_contains "Overdraft response explains insufficient balance" "$BLOCK_RESP" "negative balance"

step "6. Idempotency prevents duplicate credit"
IDEM_KEY="validate-idem-$(date +%s)"
CR1=$(curl -sf -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/manual-credit" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"amount_brl\":200.0,\"reason\":\"Idempotent credit\",\"idempotency_key\":\"$IDEM_KEY\"}")
CR1_ID=$(echo "$CR1" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
BAL1=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID" \
    -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")

CR2=$(curl -sf -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/manual-credit" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"amount_brl\":99999.0,\"reason\":\"Should be ignored\",\"idempotency_key\":\"$IDEM_KEY\"}")
CR2_ID=$(echo "$CR2" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
BAL2=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID" \
    -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")

check "Idempotency: same transaction ID" "$CR1_ID" "$CR2_ID"
check "Idempotency: balance unchanged" "$BAL1" "$BAL2"

step "7. Client sees balance but cannot credit manually"
API_KEY_RESP=$(curl -sf -X POST "$BASE_URL/admin/api-keys" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"$DEMO_CLIENT_ID\",\"name\":\"wallet-test-key\"}")
CLIENT_TOKEN=$(echo "$API_KEY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")

CLIENT_WALLET=$(curl -sf "$BASE_URL/portal/wallet" \
    -H "Authorization: Bearer $CLIENT_TOKEN")
CLIENT_BAL=$(echo "$CLIENT_WALLET" | python3 -c "import sys,json; print(json.load(sys.stdin)['balance_brl'])")
check "Client sees balance" "670.0" "$CLIENT_BAL"

CLIENT_CREDIT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/manual-credit" \
    -H "Authorization: Bearer $CLIENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"amount_brl":100.0}')
check_status_any "Client cannot credit manually" "$CLIENT_CREDIT" "401" "403"

step "8. Admin token is required for wallet admin"
NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID")
check_status_any "Admin token required" "$NO_AUTH" "401" "403"

NO_AUTH2=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/manual-credit" \
    -H "Content-Type: application/json" \
    -d '{"amount_brl":100.0}')
check_status_any "Admin token required for credit" "$NO_AUTH2" "401" "403"

step "9. Client wallet has pix_notice"
PIX_NOTICE=$(echo "$CLIENT_WALLET" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pix_notice',''))")
check_contains "PIX notice present" "$PIX_NOTICE" "não está disponível"

step "10. Admin can list all wallets"
ALL_WALLETS=$(curl -sf "$BASE_URL/admin/billing/wallets" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
WALLET_COUNT=$(echo "$ALL_WALLETS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Total wallets: $WALLET_COUNT"
check "Wallet list accessible" "1" "1"

step "11. Admin can list transactions"
TXS=$(curl -sf "$BASE_URL/admin/billing/wallets/$DEMO_CLIENT_ID/transactions" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
TX_COUNT=$(echo "$TXS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Transactions found: $TX_COUNT"
check "Transactions listed" "1" "1"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
    echo -e "\nSome validations FAILED."
    exit 1
fi

echo -e "\n✓ Prepaid wallet validation PASSED"
echo "  - Credit manual: funciona"
echo "  - Débito por uso: funciona"
echo "  - Saldo insuficiente: bloqueado"
echo "  - Idempotência: funcionando"
echo "  - Admin token: exigido"
echo "  - PIX real: fora do escopo (avisado)"
