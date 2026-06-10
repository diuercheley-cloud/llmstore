#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"
FED_TOKEN="${COMMERCIAL_FEDERATION_SHARED_TOKEN:-shared-fed-token}"

echo "=== Validating Commercial Federation ==="

clusters_before="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/clusters")"
echo "${clusters_before}" | grep -q '"clusters"' || (echo "clusters list failed" && exit 1)

create_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/federation/clusters" \
  -d '{"cluster_id":"validate-remote","name":"Validate Remote","region":"lab","environment":"staging","status":"active","tenant_scope_json":{"tenants":["tenant-validate"],"allow_untagged":false},"metadata_json":{"api_key":"secret","note":"safe"}}')"
echo "${create_resp}" | grep -q '"cluster"' || (echo "cluster create failed" && exit 1)
echo "${create_resp}" | grep -q '\[REDACTED\]' || (echo "cluster metadata sanitization failed" && exit 1)

payload='{"source_cluster_id":"validate-remote","aggregates":[{"bucket_start":"2026-05-14T00:00:00+00:00","bucket_minutes":5,"provider":"openai","model":"gpt-4o-mini","client_id":"client-validate","tenant_id":"tenant-validate","requests_count":3,"actual_cost_brl":1.25,"actual_margin_brl":0.75,"avg_latency_ms":120,"received_at":"2026-05-14T00:05:00+00:00"}]}'
ingest_resp="$(curl -sS -X POST -H "X-Federation-Token: ${FED_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/federation/ingest" \
  -d "${payload}")"
echo "${ingest_resp}" | grep -q '"records_processed": 1\|"records_processed":1' || (echo "federation ingest failed" && exit 1)

dup_resp="$(curl -sS -X POST -H "X-Federation-Token: ${FED_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/federation/ingest" \
  -d "${payload}")"
echo "${dup_resp}" | grep -q '"records_duplicate": 1\|"records_duplicate":1' || (echo "duplicate federation ingest failed" && exit 1)

overview_resp="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/overview")"
echo "${overview_resp}" | grep -q '"clusters"' || (echo "overview failed" && exit 1)

compare_resp="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/compare")"
echo "${compare_resp}" | grep -q '"comparisons"' || (echo "compare failed" && exit 1)

export_json="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/export?format=json")"
echo "${export_json}" | grep -q '"overview"' || (echo "federation json export failed" && exit 1)

export_csv="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/export?format=csv")"
echo "${export_csv}" | grep -q 'source_cluster_id' || (echo "federation csv export failed" && exit 1)

export_html="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/export?format=html")"
echo "${export_html}" | grep -q 'Commercial Federation' || (echo "federation html export failed" && exit 1)

sync_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/federation/sync/manual" -d '{}')"
echo "${sync_resp}" | grep -q '"executed"' || (echo "manual sync endpoint failed" && exit 1)

cleanup_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/federation/cleanup")"
echo "${cleanup_resp}" | grep -q '"retention_days"' || (echo "federation cleanup failed" && exit 1)

echo "=== Commercial Federation Validation Successful ==="
