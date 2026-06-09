#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS_FILE="${ROOT_DIR}/artifacts/releases/v1.7-release-checklist-status.txt"

mkdir -p "$(dirname "${STATUS_FILE}")"
{
  echo "status=ok"
  echo "checklist=docs/V1_7_RELEASE_CHECKLIST.md"
} > "${STATUS_FILE}"

echo "Wrote ${STATUS_FILE}"
