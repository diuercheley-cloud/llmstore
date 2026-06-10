#!/usr/bin/env bash
# scripts/backup/clean-sensitive-artifacts-local.sh
# Safely cleans or redacts sensitive local artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# shellcheck source=/dev/null
if [[ -f "${SCRIPT_DIR}/../dev/common.sh" ]]; then
  source "${SCRIPT_DIR}/../dev/common.sh"
else
  echo "Error: common.sh not found in ${SCRIPT_DIR}"
  exit 1
fi

# shellcheck source=/dev/null
if [[ -f "${SCRIPT_DIR}/lib/redaction.sh" ]]; then
  source "${SCRIPT_DIR}/../dev/lib/redaction.sh"
else
  echo "Error: lib/redaction.sh not found in ${SCRIPT_DIR}"
  exit 1
fi

# Constants
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/security-artifact-cleanup/${TIMESTAMP}"
VERSIONED_RELEASE_FILES=(
  "summary.json"
  "summary.md"
  "release-manifest.json"
  "bundle-manifest.json"
  "bundle-checksums.sha256"
)

# Default variables
DRY_RUN=true
YES=false
OLDER_THAN_DAYS=""
KEEP_LAST=""
SECTION="all"
REDACT_ONLY=false

usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --dry-run             Show what would be done (default)"
  echo "  --yes                 Execute deletion/redaction"
  echo "  --older-than-days N   Only consider artifacts older than N days"
  echo "  --section SECTION     Section to clean: security-reports|validation|demo|production-readiness|all (default: all)"
  echo "  --keep-last N         Keep the last N artifacts for each section"
  echo "  --redact-instead-of-delete Redact sensitive data instead of deleting files"
  echo "  --help                Show this help"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --yes) YES=true; DRY_RUN=false; shift ;;
    --older-than-days) OLDER_THAN_DAYS="$2"; shift 2 ;;
    --section) SECTION="$2"; shift 2 ;;
    --keep-last) KEEP_LAST="$2"; shift 2 ;;
    --redact-instead-of-delete) REDACT_ONLY=true; shift ;;
    --help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

# Initialize reports
mkdir -p "${REPORT_DIR}"
CANDIDATES=()
PROCESSED=()
DELETED=()
REDACTED=()
SKIPPED=()
NEEDS_MANUAL_REVIEW=()
WARNINGS=()
ERRORS=()

log_warning() {
  echo "Warning: $1"
  WARNINGS+=("$1")
}

log_error() {
  echo "Error: $1"
  ERRORS+=("$1")
}

is_tracked() {
  local file="$1"
  git ls-files --error-unmatch "$file" >/dev/null 2>&1
}

is_ignored() {
  local file="$1"
  git check-ignore -q "$file"
}

is_versioned_release_file() {
  local file="$1"
  local filename
  filename=$(basename "$file")
  
  # Check if it is in a releases/ subdirectory
  if [[ "$file" == *"/releases/"* ]]; then
    for protected in "${VERSIONED_RELEASE_FILES[@]}"; do
      if [[ "$filename" == "$protected" ]]; then
        return 0
      fi
    done
  fi
  return 1
}

# Define sections and their patterns
declare -A SECTION_PATTERNS=(
  ["security-reports"]="artifacts/security-reports/*"
  ["validation"]="artifacts/*validation*/* artifacts/validation/* artifacts/quality/*"
  ["demo"]="artifacts/local-demo/*"
  ["production-readiness"]="artifacts/production-readiness/*"
)

get_section_items() {
  local sect="$1"
  local patterns=""
  if [[ "$sect" == "all" ]]; then
    patterns="artifacts/*"
  else
    patterns="${SECTION_PATTERNS[$sect]:-}"
  fi

  if [[ -z "$patterns" && "$sect" != "all" ]]; then
    log_error "Unknown section: $sect"
    return 1
  fi

  local items=()
  # Disable globbing temporarily to safely split patterns into individual patterns
  local prev_f=$(set +o | grep noglob || true)
  set -f
  # shellcheck disable=SC2206
  local pat_list=($patterns)
  eval "$prev_f"

  for p in "${pat_list[@]}"; do
    # shellcheck disable=SC2086
    for item in ${PROJECT_ROOT}/$p; do
      [[ -e "$item" ]] || continue
      items+=("$item")
    done
  done

  # De-duplicate
  if [[ ${#items[@]} -gt 0 ]]; then
    printf "%s\n" "${items[@]}" | sort -u
  fi
}

# Gather candidates
SECTIONS_TO_PROCESS=()
if [[ "$SECTION" == "all" ]]; then
  SECTIONS_TO_PROCESS=("all")
else
  SECTIONS_TO_PROCESS=("$SECTION")
fi

FILES_TO_PROCESS=()

for sect in "${SECTIONS_TO_PROCESS[@]}"; do
  # Read items into an array line by line
  ITEMS=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && ITEMS+=("$line")
  done < <(get_section_items "$sect")
  
  if [[ ${#ITEMS[@]} -eq 0 ]]; then continue; fi

  # Apply --older-than-days
  FILTERED_ITEMS=()
  if [[ -n "$OLDER_THAN_DAYS" ]]; then
    for item in "${ITEMS[@]}"; do
      # If OLDER_THAN_DAYS is -1, we include everything
      if [[ "$OLDER_THAN_DAYS" == "-1" ]]; then
        FILTERED_ITEMS+=("$item")
      elif [[ $(find "$item" -maxdepth 0 -mtime +"$OLDER_THAN_DAYS" 2>/dev/null) ]]; then
        FILTERED_ITEMS+=("$item")
      fi
    done
  else
    FILTERED_ITEMS=("${ITEMS[@]}")
  fi

  # Apply --keep-last
  if [[ -n "$KEEP_LAST" && ${#FILTERED_ITEMS[@]} -gt "$KEEP_LAST" ]]; then
    # Sort by modification time, newest first, and take the ones after KEEP_LAST
    # shellcheck disable=SC2012
    OLD_ITEMS=$(ls -dt "${FILTERED_ITEMS[@]}" 2>/dev/null | tail -n +$((KEEP_LAST + 1)))
    while IFS= read -r item; do
      [[ -n "$item" ]] && CANDIDATES+=("$item")
    done <<< "$OLD_ITEMS"
  elif [[ -z "$KEEP_LAST" ]]; then
    # If keep-last is NOT specified, we take all filtered items as candidates
    for item in "${FILTERED_ITEMS[@]}"; do
      CANDIDATES+=("$item")
    done
  fi
done

# Deduplicate candidates
if [[ ${#CANDIDATES[@]} -gt 0 ]]; then
  IFS=$'\n' read -rd '' -a FINAL_CANDIDATES < <(printf "%s\n" "${CANDIDATES[@]}" | sort -u) || true
else
  FINAL_CANDIDATES=()
fi

echo "Found ${#FINAL_CANDIDATES[@]} candidate artifacts."

# Process candidates
for c in "${FINAL_CANDIDATES[@]}"; do
  # Recurse if directory
  if [[ -d "$c" ]]; then
    while IFS= read -r f; do
      FILES_TO_PROCESS+=("$f")
    done < <(find "$c" -type f)
  else
    FILES_TO_PROCESS+=("$c")
  fi
done

# Deduplicate files
if [[ ${#FILES_TO_PROCESS[@]} -gt 0 ]]; then
    IFS=$'\n' read -rd '' -a UNIQUE_FILES < <(printf "%s\n" "${FILES_TO_PROCESS[@]}" | sort -u) || true
else
    UNIQUE_FILES=()
fi

for f in "${UNIQUE_FILES[@]}"; do
  if is_tracked "$f"; then
    NEEDS_MANUAL_REVIEW+=("$f")
    SKIPPED+=("$f")
    continue
  fi

  if is_versioned_release_file "$f"; then
    SKIPPED+=("$f")
    continue
  fi

  # Only process files in artifacts/ or releases/ (security-reports might be in releases/ too if generated there)
  # But we already checked is_tracked and is_versioned_release_file.
  
  if [[ "$REDACT_ONLY" == "true" ]]; then
    # Only redact .md, .json, .log, .txt
    if [[ "$f" =~ \.(md|json|log|txt)$ ]]; then
      if [[ "$DRY_RUN" == "true" ]]; then
        REDACTED+=("$f")
      else
        if redact_file_inplace "$f"; then
          REDACTED+=("$f")
        else
          log_error "Failed to redact: $f"
        fi
      fi
    else
      SKIPPED+=("$f")
    fi
  else
    if [[ "$DRY_RUN" == "true" ]]; then
      DELETED+=("$f")
    else
      if rm -f "$f"; then
        DELETED+=("$f")
      else
        log_error "Failed to delete: $f"
      fi
    fi
  fi
done

# Final Report Generation
MODE="execute"
[[ "$DRY_RUN" == "true" ]] && MODE="dry-run"

# JSON Report
REPORT_JSON="${REPORT_DIR}/cleanup-report.json"
cat <<EOF > "${REPORT_JSON}"
{
  "timestamp": "${TIMESTAMP}",
  "mode": "${MODE}",
  "config": {
    "section": "${SECTION}",
    "older_than_days": "${OLDER_THAN_DAYS:-null}",
    "keep_last": "${KEEP_LAST:-null}",
    "redact_only": ${REDACT_ONLY}
  },
  "summary": {
    "total_files_identified": ${#UNIQUE_FILES[@]},
    "deleted": ${#DELETED[@]},
    "redacted": ${#REDACTED[@]},
    "skipped": ${#SKIPPED[@]},
    "needs_manual_review": ${#NEEDS_MANUAL_REVIEW[@]},
    "errors": ${#ERRORS[@]}
  },
  "deleted": $(printf '%s\n' "${DELETED[@]}" | jq -R . | jq -s .),
  "redacted": $(printf '%s\n' "${REDACTED[@]}" | jq -R . | jq -s .),
  "skipped": $(printf '%s\n' "${SKIPPED[@]}" | jq -R . | jq -s .),
  "needs_manual_review": $(printf '%s\n' "${NEEDS_MANUAL_REVIEW[@]}" | jq -R . | jq -s .),
  "errors": $(printf '%s\n' "${ERRORS[@]}" | jq -R . | jq -s .),
  "warnings": $(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .)
}
EOF

# MD Report
REPORT_MD="${REPORT_DIR}/cleanup-report.md"
cat <<EOF > "${REPORT_MD}"
# Security Artifact Cleanup Report - ${TIMESTAMP}

- **Mode:** ${MODE}
- **Section:** ${SECTION}
- **Action:** $([[ "$REDACT_ONLY" == "true" ]] && echo "Redaction" || echo "Deletion")

## Summary
- **Total Files Identified:** ${#UNIQUE_FILES[@]}
- **Deleted:** ${#DELETED[@]}
- **Redacted:** ${#REDACTED[@]}
- **Skipped:** ${#SKIPPED[@]}
- **Needs Manual Review (Tracked Files):** ${#NEEDS_MANUAL_REVIEW[@]}
- **Errors:** ${#ERRORS[@]}

## Needs Manual Review (Tracked)
$(for f in "${NEEDS_MANUAL_REVIEW[@]}"; do echo "- \`$f\`"; done)

## Deleted
$(for f in "${DELETED[@]}"; do echo "- \`$f\`"; done)

## Redacted
$(for f in "${REDACTED[@]}"; do echo "- \`$f\`"; done)

## Skipped
$(for f in "${SKIPPED[@]}"; do echo "- \`$f\`"; done)

EOF

if [[ ${#ERRORS[@]} -gt 0 ]]; then
cat <<EOF >> "${REPORT_MD}"
## Errors
$(for e in "${ERRORS[@]}"; do echo "- $e"; done)
EOF
fi

echo "Cleanup report generated at:"
echo "  JSON: ${REPORT_JSON}"
echo "  MD:   ${REPORT_MD}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN COMPLETE. No changes were made."
fi
