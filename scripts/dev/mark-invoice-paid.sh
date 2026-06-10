#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

INVOICE_ID="${1:?usage: ./scripts/dev/mark-invoice-paid.sh INVOICE_ID [PAYMENT_REFERENCE] [AMOUNT] [NOTE]}"
PAYMENT_REFERENCE="${2:-local-manual-ref}"
AMOUNT="${3:-}"
NOTE="${4:-Pagamento confirmado manualmente (Billing local/manual)}"

payload="$(
python3 -c '
import json, sys
invoice_id = sys.argv[1]
payment_reference = sys.argv[2]
amount = sys.argv[3]
note = sys.argv[4]
data = {
    "payment_method": "manual_pix",
    "payment_reference": payment_reference,
    "note": note,
}
if amount:
    data["amount_paid"] = float(amount)
print(json.dumps(data))
' "${INVOICE_ID}" "${PAYMENT_REFERENCE}" "${AMOUNT}" "${NOTE}"
)"

if response="$(curl -fsS "${BASE_URL}/admin/billing/invoices/${INVOICE_ID}/mark-paid" -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -X PATCH -d "${payload}" 2>/dev/null)"; then
  printf '%s\n' "${response}" | python3 -m json.tool
  exit 0
fi

dc exec -T control-plane bash -lc \
  "curl -fsS http://localhost:8080/admin/billing/invoices/${INVOICE_ID}/mark-paid -H 'X-Admin-Token: ${ADMIN_TOKEN}' -H 'Content-Type: application/json' -X PATCH -d '${payload}'" | python3 -m json.tool
