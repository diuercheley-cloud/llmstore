#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

CLIENT_ID="${1:-}"
DUE_IN_DAYS="${2:-7}"
PAYMENT_INSTRUCTIONS="${3:-Pagamento manual/local. Sem PIX real nesta versão. Confirmar no admin.}"

payload="$(
python3 -c '
import json, sys
client_id = sys.argv[1]
due_in_days = int(sys.argv[2])
instructions = sys.argv[3]
data = {
    "due_in_days": due_in_days,
    "payment_method": "manual_pix",
    "payment_instructions": instructions,
}
if client_id:
    data["client_id"] = client_id
print(json.dumps(data))
' "${CLIENT_ID}" "${DUE_IN_DAYS}" "${PAYMENT_INSTRUCTIONS}"
)"

if response="$(curl -fsS "${BASE_URL}/admin/billing/invoices/generate" -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -d "${payload}" 2>/dev/null)"; then
  printf '%s\n' "${response}" | python3 -m json.tool
  exit 0
fi

dc exec -T control-plane bash -lc \
  "curl -fsS http://localhost:8080/admin/billing/invoices/generate -H 'X-Admin-Token: ${ADMIN_TOKEN}' -H 'Content-Type: application/json' -d '${payload}'" | python3 -m json.tool
