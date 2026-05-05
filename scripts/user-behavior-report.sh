#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

printf '=== USER BEHAVIOR REPORT ===\n'
BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  printf 'ERROR: ADMIN_TOKEN not set. Cannot pull report.\n'
  exit 1
fi

clients_json="$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}")"

printf '\n1. Onboarding Status\n'
printf '%s\n' "${clients_json}" | python3 -c '
import json, sys
clients = json.load(sys.stdin)
total = len(clients)
finished = 0
for c in clients:
    meta = json.loads(c.get("metadata_json") or "{}")
    if meta.get("onboarding_finished"):
        finished += 1
percentage = (finished / total * 100) if total > 0 else 0
print(f"Total Clients: {total}")
print(f"Finished Onboarding: {finished} ({percentage:.1f}%)")
'

printf '\n2. Usage Summary (Top 5)\n'
usage_json="$(curl -fsS "${BASE_URL}/admin/usage/summary" -H "X-Admin-Token: ${ADMIN_TOKEN}")"
printf '%s\n' "${usage_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
clients = data.get("clients", [])
# Sort by monthly usage
clients.sort(key=lambda x: x.get("monthly_usage", {}).get("used_tokens", 0), reverse=True)
for c in clients[:5]:
    name = c.get("name", "<unknown>")
    monthly = c.get("monthly_usage", {}).get("used_tokens", 0)
    status = c.get("billing_status", "<unknown>")
    print(f"Client: {name} | Monthly: {monthly} tokens | Status: {status}")
'

printf '\n3. Recent Security Events\n'
events_json="$(curl -fsS "${BASE_URL}/admin/security/events" -H "X-Admin-Token: ${ADMIN_TOKEN}")"
printf '%s\n' "${events_json}" | python3 -c '
import json, sys
events = json.load(sys.stdin)
for e in events[:5]:
    created_at = e.get("created_at", "<unknown>")
    severity = str(e.get("severity", "unknown")).upper()
    title = e.get("title", "<unknown>")
    print(f"[{created_at}] {severity}: {title}")
'

printf '\n=== REPORT END ===\n'
