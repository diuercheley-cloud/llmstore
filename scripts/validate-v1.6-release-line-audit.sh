#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_SUMMARY_DOC="${ROOT}/docs/V1_6_AUDIT_SUMMARY.md"
AUDIT_BASE="${ROOT}/artifacts/final-qa/v1.6-audit"

if [[ ! -f "${AUDIT_SUMMARY_DOC}" ]]; then
  echo "Missing ${AUDIT_SUMMARY_DOC}" >&2
  exit 1
fi

if [[ ! -d "${AUDIT_BASE}" ]]; then
  echo "Missing ${AUDIT_BASE}" >&2
  exit 1
fi

LATEST_DIR="$(find "${AUDIT_BASE}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
if [[ -z "${LATEST_DIR}" ]]; then
  echo "No audit directories found under ${AUDIT_BASE}" >&2
  exit 1
fi

if [[ ! -s "${LATEST_DIR}/v1.6-audit.json" ]]; then
  echo "Missing audit JSON in ${LATEST_DIR}" >&2
  exit 1
fi

if [[ ! -s "${LATEST_DIR}/v1.6-audit.md" ]]; then
  echo "Missing audit markdown in ${LATEST_DIR}" >&2
  exit 1
fi

grep -q "v1.6.6-repo-cleanup" "${AUDIT_SUMMARY_DOC}"
grep -q "v1.6.0-openai-compat" "${LATEST_DIR}/v1.6-audit.json"

echo "v1.6 audit validation passed"
