#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "${ROOT_DIR}/docs/V1_7_RELEASE_CHECKLIST.md" ]]; then
  echo "Missing docs/V1_7_RELEASE_CHECKLIST.md"
  exit 1
fi

echo "V1.7 release checklist validation passed."
