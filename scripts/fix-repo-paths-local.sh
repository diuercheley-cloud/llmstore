#!/usr/bin/env bash
# Suggest or apply fixes for broken repo paths.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/repo-cleanup/${TIMESTAMP}"
DRY_RUN=true
APPLY=false
FIXES=()

mkdir -p "${REPORT_DIR}"

usage() {
  echo "Usage: $0 [--dry-run|--apply]"
  echo "  --dry-run  (default) Only show suggested fixes"
  echo "  --apply    Apply safe substitutions"
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --apply)   APPLY=true; DRY_RUN=false; shift ;;
    --help)    usage ;;
    *)         echo "Unknown: $1"; usage ;;
  esac
done

maybe_fix() {
  local file="$1"
  local old="$2"
  local new="$3"
  local reason="$4"
  if grep -qF "$old" "$file" 2>/dev/null; then
    FIXES+=("$file: $old -> $new ($reason)")
    if $APPLY; then
      cp "$file" "${file}.bak.${TIMESTAMP}"
      sed -i "s|$old|$new|g" "$file"
    fi
  fi
}

echo "=== Repo Path Fixer ==="
echo "Mode: $($DRY_RUN && echo 'DRY-RUN (no changes)' || echo 'APPLY')"
echo ""

# Scan all shell scripts for known broken patterns
while IFS= read -r -d '' sh; do
  rel="${sh#$PROJECT_ROOT/}"

  # Pattern: source with $(dirname "$0") instead of BASH_SOURCE (unless it also uses BASH_SOURCE)
  if grep -qP 'source\s+\$\(dirname\s+\$0\)' "$sh" 2>/dev/null; then
    FIXES+=("$rel: has source with \$(dirname \$0) — consider replacing with \${BASH_SOURCE[0]}")
  fi

  # Pattern: ROOT_DIR/lib/ (should be ROOT_DIR/scripts/lib/ after migration)
  if grep -qP 'source\s+.*ROOT_DIR\}/lib/' "$sh" 2>/dev/null; then
    maybe_fix "$sh" '${ROOT_DIR}/lib/' '${ROOT_DIR}/scripts/lib/' "lib migration to scripts/lib/"
  fi

  # Pattern: ../lib/ relative (should be lib/ since SCRIPT_DIR is scripts/)
  if grep -qP 'source\s+.*SCRIPT_DIR\}/\.\./lib/' "$sh" 2>/dev/null; then
    maybe_fix "$sh" '${SCRIPT_DIR}/../lib/' '${SCRIPT_DIR}/lib/' "fragile ../lib/ -> lib/"
  fi

done < <(find "${PROJECT_ROOT}/scripts" -maxdepth 2 -name '*.sh' -type f -print0 2>/dev/null)

# Report
echo "Summary: ${#FIXES[@]} potential fix(es) found"
echo ""

if [[ ${#FIXES[@]} -gt 0 ]]; then
  echo "Fixes:"
  for f in "${FIXES[@]}"; do
    echo "  - $f"
  done
  echo ""
fi

REPORT_FILE="${REPORT_DIR}/fix-report.md"
{
  echo "# Repo Path Fix Report"
  echo "**Timestamp:** ${TIMESTAMP}"
  echo "**Mode:** $($DRY_RUN && echo 'DRY-RUN' || echo 'APPLIED')"
  echo ""
  echo "## Summary"
  echo "- **Fixes found:** ${#FIXES[@]}"
  echo "- **Applied:** $($APPLY && echo 'yes' || echo 'no')"
  echo ""
  if [[ ${#FIXES[@]} -gt 0 ]]; then
    echo "## Changes"
    for f in "${FIXES[@]}"; do echo "- ${f}"; done
    echo ""
  fi
} > "$REPORT_FILE"

echo "Report: ${REPORT_FILE}"
