#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"

headers=(-H "Content-Type: application/json" -H "X-Admin-Token: ${ADMIN_TOKEN}")

echo "Validating model supply chain endpoints against ${BASE_URL}"

register_payload='{
  "model_name": "validation/model",
  "model_alias": "validation-model",
  "provider": "openai_compatible",
  "model_format": "api",
  "tenant_scope_json": {"client_names": ["validation-tenant"]}
}'

register_resp="$(curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/register" -d "${register_payload}")"
entry_id="$(printf '%s' "${register_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/${entry_id}/verify" >/dev/null
curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/${entry_id}/approve" -d '{"approved_by":"validator"}' >/dev/null
curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/${entry_id}/quarantine" -d '{"reason":"validation quarantine"}' >/dev/null
curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/${entry_id}/revoke" -d '{"reason":"validation revoke","revocation_type":"manual"}' >/dev/null

prov_resp="$(curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/provenance" -d '{"source_type":"manual","import_method":"manual","artifact_hash":"validation-artifact","evidence_json":{"api_key":"should-redact","scanner":"validation"}}')"
prov_id="$(printf '%s' "${prov_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

bundle_create="$(curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/register" -d "{\"model_name\":\"bundle/validation\",\"model_alias\":\"bundle-validation\",\"model_format\":\"api\",\"provenance_id\":\"${prov_id}\"}")"
bundle_entry_id="$(printf '%s' "${bundle_create}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/${bundle_entry_id}/approve" -d '{"approved_by":"validator"}' >/dev/null
bundle_resp="$(curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/bundles" -d "{\"bundle_name\":\"validation-bundle\",\"registry_entry_id\":\"${bundle_entry_id}\",\"source_cluster_id\":\"cluster-a\",\"target_cluster_id\":\"cluster-b\"}")"
bundle_id="$(printf '%s' "${bundle_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl -fsS "${headers[@]}" -X POST "${BASE_URL}/admin/models/supply-chain/bundles/${bundle_id}/verify" >/dev/null

status_resp="$(curl -fsS "${headers[@]}" "${BASE_URL}/admin/models/supply-chain/status")"
printf '%s' "${status_resp}" | grep -q '"enforcement_mode"'
if printf '%s' "${status_resp}" | grep -qi 'sk-'; then
  echo "Sensitive payload leaked in status response" >&2
  exit 1
fi

echo "Model supply chain validation completed"
