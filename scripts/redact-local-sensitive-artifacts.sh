#!/usr/bin/env bash
set -euo pipefail

# Removes local generated artifacts that may embed demo or admin secrets in raw logs.
# This operates only on local artifacts directories and does not touch versioned source files.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

removed_any=false

if [[ -d "${ROOT_DIR}/artifacts" ]]; then
  while IFS= read -r target; do
    rm -rf "${target}"
    printf 'Removed local artifact directory: %s\n' "${target}"
    removed_any=true
  done < <(find "${ROOT_DIR}/artifacts" -mindepth 1 -maxdepth 1 -type d | sort)
fi

if [[ "${removed_any}" == false ]]; then
  printf 'No sensitive local artifacts to remove.\n'
fi
