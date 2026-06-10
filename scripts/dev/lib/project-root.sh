#!/usr/bin/env bash
# Helper to resolve the project root from any script location.
# Usage:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/project-root.sh"
#   PROJECT_ROOT="$(resolve_project_root "${BASH_SOURCE[0]}")"

resolve_project_root() {
  local script_path="$1"
  if [[ -z "${script_path}" ]]; then
    script_path="${BASH_SOURCE[1]:-}"
  fi
  if [[ -z "${script_path}" ]]; then
    script_path="$0"
  fi
  cd "$(dirname "${script_path}")/.." && pwd
}
