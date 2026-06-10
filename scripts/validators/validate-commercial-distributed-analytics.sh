#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"

echo "=== Validating Commercial Distributed Analytics ==="

nodes_resp="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/nodes")"
echo "${nodes_resp}" | grep -q '"nodes"' || (echo "nodes endpoint failed" && exit 1)

overview_resp="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/cluster-overview")"
echo "${overview_resp}" | grep -q '"cluster_id"' || (echo "cluster overview endpoint failed" && exit 1)

payload='{"request_id":"validate-dist-1","correlation_id":"validate-corr-1","selected_provider":"openai","authorization":"Bearer sk-secret-value","prompt":"should-not-persist"}'
ingest_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/distributed/ingest?process_now=true" \
  -d "${payload}")"
echo "${ingest_resp}" | grep -q '"accepted"' || (echo "ingest endpoint failed" && exit 1)
echo "${ingest_resp}" | grep -q '\[REDACTED\]' || (echo "payload sanitization failed" && exit 1)

dup_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  "${API_BASE_URL}/admin/routing/distributed/ingest?process_now=true" \
  -d "${payload}")"
echo "${dup_resp}" | grep -q '"duplicate"' || (echo "duplicate ingest validation failed" && exit 1)

rebuild_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/rebuild-aggregates?hours=24")"
echo "${rebuild_resp}" | grep -q '"buckets_rebuilt"' || (echo "rebuild aggregates failed" && exit 1)

export_json="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/export?format=json")"
echo "${export_json}" | grep -q '"cluster_overview"' || (echo "json export failed" && exit 1)

export_csv="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/export?format=csv")"
echo "${export_csv}" | grep -q 'bucket_start' || (echo "csv export failed" && exit 1)

export_html="$(curl -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/export?format=html")"
echo "${export_html}" | grep -q 'Commercial Cluster Analytics' || (echo "html export failed" && exit 1)

cleanup_resp="$(curl -sS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" "${API_BASE_URL}/admin/routing/distributed/cleanup")"
echo "${cleanup_resp}" | grep -q '"retention_days"' || (echo "cleanup retention failed" && exit 1)

echo "=== Commercial Distributed Analytics Validation Successful ==="
