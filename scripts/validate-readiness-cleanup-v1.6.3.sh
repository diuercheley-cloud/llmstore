#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "${ROOT_DIR}/docs/READINESS_CLEANUP_v1.6.3.md" ]]; then
  echo "Missing docs/READINESS_CLEANUP_v1.6.3.md"
  exit 1
fi

echo "Readiness cleanup validation passed."
