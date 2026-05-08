#!/usr/bin/env bash
# scripts/retention-local.sh - Local retention policy implementation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# shellcheck source=/dev/null
if [[ -f "${SCRIPT_DIR}/common.sh" ]]; then
  source "${SCRIPT_DIR}/common.sh"
  init_stack_env
else
  echo "Error: common.sh not found in ${SCRIPT_DIR}"
  exit 1
fi

# Constants
DEFAULT_CONFIG="${PROJECT_ROOT}/config/retention-example.json"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/retention/${TIMESTAMP}"
PROTECTED_PATHS=(
  "${PROJECT_ROOT}/models"
  "${PROJECT_ROOT}/scripts"
  "${PROJECT_ROOT}/docs"
  "${PROJECT_ROOT}/.git"
  "${PROJECT_ROOT}/.venv"
)
PROTECTED_FILES=(
  ".env"
  ".env.local"
  "GEMINI.md"
)

# Variables
DRY_RUN=false
YES=false
CONFIG_PATH="${DEFAULT_CONFIG}"
SECTION="all"
OLDER_THAN_DAYS=""
KEEP_LAST=""
CLIENT_ID=""
INCLUDE_RELEASES=false

usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --dry-run             Show what would be deleted"
  echo "  --yes                 Execute deletion"
  echo "  --config PATH         Path to config JSON (default: config/retention-example.json)"
  echo "  --section SECTION     Section to clean: rag|tts|logs|artifacts|backups|all"
  echo "  --older-than-days N   Override retention days for the section"
  echo "  --keep-last N         Override keep last count for the section"
  echo "  --client-id UUID      Only clean data for specific client (RAG/TTS)"
  echo "  --include-releases    Allow cleaning releases/ (EXTREME CAUTION)"
  echo "  --help                Show this help"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --yes) YES=true; shift ;;
    --config) CONFIG_PATH="$2"; shift 2 ;;
    --section) SECTION="$2"; shift 2 ;;
    --older-than-days) OLDER_THAN_DAYS="$2"; shift 2 ;;
    --keep-last) KEEP_LAST="$2"; shift 2 ;;
    --client-id) CLIENT_ID="$2"; shift 2 ;;
    --include-releases) INCLUDE_RELEASES=true; shift ;;
    --help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

# Validation
if [[ -z "${PROJECT_ROOT}" || "${PROJECT_ROOT}" == "/" ]]; then
  echo "Error: PROJECT_ROOT is empty or /. Aborting."
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Error: Config file not found at ${CONFIG_PATH}"
  exit 1
fi

# Report data
REPORT_JSON_FILE="${REPORT_DIR}/retention-report.json"
REPORT_MD_FILE="${REPORT_DIR}/retention-report.md"
mkdir -p "${REPORT_DIR}"

CANDIDATES=()
DELETED=()
SKIPPED=()
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

is_protected() {
  local path="$1"
  local abs_path
  abs_path=$(realpath -m "$path")

  # 1. Base protections
  for p in "${PROTECTED_PATHS[@]}"; do
    if [[ "$abs_path" == "$p" || "$abs_path" == "$p"/* ]]; then
      return 0
    fi
  done

  # 2. File protections
  local filename
  filename=$(basename "$path")
  for f in "${PROTECTED_FILES[@]}"; do
    if [[ "$filename" == "$f" ]]; then
      return 0
    fi
  done

  # 3. .gguf protection
  if [[ "$path" == *.gguf ]]; then
    return 0
  fi

  # 4. Outside project root
  if [[ "$abs_path" != "${PROJECT_ROOT}"/* ]]; then
    return 0
  fi

  # 5. Releases protection (unless explicitly allowed)
  if [[ "${INCLUDE_RELEASES}" == "false" ]]; then
    if [[ "$abs_path" == "${PROJECT_ROOT}/releases" || "$abs_path" == "${PROJECT_ROOT}/releases"/* ]]; then
      return 0
    fi
  fi

  return 1
}

get_config_value() {
  local key="$1"
  jq -r ".$key" "${CONFIG_PATH}"
}

# --- SECTION: RAG ---
clean_rag() {
  local ret_days="${OLDER_THAN_DAYS:-$(get_config_value "rag_uploads_retention_days")}"
  if [[ "${ret_days}" == "null" && -z "${CLIENT_ID}" ]]; then
     return 0
  fi

  local rag_dirs=(
    "${PROJECT_ROOT}/data/rag_uploads"
    "${PROJECT_ROOT}/data/rag_uploads-"*
  )

  for base_dir in "${rag_dirs[@]}"; do
    [[ -d "$base_dir" ]] || continue
    
    if [[ -n "${CLIENT_ID}" ]]; then
      if [[ -d "${base_dir}/${CLIENT_ID}" ]]; then
        CANDIDATES+=("${base_dir}/${CLIENT_ID}")
      fi
    else
      for d in "${base_dir}"/*; do
        [[ -e "$d" ]] || continue
        if [[ "${ret_days}" != "null" ]]; then
          if [[ $(find "$d" -maxdepth 0 -mtime +"${ret_days}") ]]; then
            CANDIDATES+=("$d")
          fi
        else
          CANDIDATES+=("$d")
        fi
      done
    fi
  done
}

# --- SECTION: TTS ---
clean_tts() {
  local ret_days="${OLDER_THAN_DAYS:-$(get_config_value "tts_audio_retention_days")}"
  if [[ "${ret_days}" == "null" ]]; then return 0; fi

  # Find .wav files in specific places
  local search_dirs=("${PROJECT_ROOT}/data" "${PROJECT_ROOT}/artifacts")
  [[ -f "${PROJECT_ROOT}/output.wav" ]] && CANDIDATES+=("${PROJECT_ROOT}/output.wav")

  for d in "${search_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r f; do
      [[ -n "$f" ]] || continue
      # If client-id specified, check if it is in the path or maybe we skip for now if not clear
      if [[ -n "${CLIENT_ID}" ]]; then
         if [[ "$f" != *"${CLIENT_ID}"* ]]; then continue; fi
      fi
      CANDIDATES+=("$f")
    done < <(find "$d" -name "*.wav" -type f -mtime +"${ret_days}" 2>/dev/null || true)
  done
}

# --- SECTION: LOGS ---
clean_logs() {
  local ret_days="${OLDER_THAN_DAYS:-$(get_config_value "logs_retention_days")}"
  if [[ "${ret_days}" == "null" ]]; then return 0; fi

  local log_dir="${PROJECT_ROOT}/logs"
  if [[ -d "$log_dir" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" ]] && CANDIDATES+=("$f")
    done < <(find "$log_dir" -type f -mtime +"${ret_days}" 2>/dev/null || true)
  fi
}

# --- SECTION: ARTIFACTS ---
clean_artifacts() {
  # Map config keys to directory patterns
  declare -A artifact_maps=(
    ["validation_artifacts_keep_last"]="artifacts/*validation*/* artifacts/validation/* artifacts/quality/*"
    ["demo_artifacts_keep_last"]="artifacts/local-demo/*"
    ["security_reports_keep_last"]="artifacts/security-reports/*"
    ["production_readiness_keep_last"]="artifacts/production-readiness/*"
    ["dr_artifacts_keep_last"]="artifacts/dr-tests*/*"
    ["model_benchmarks_keep_last"]="artifacts/*benchmark*/*"
  )

  for key in "${!artifact_maps[@]}"; do
    local keep="${KEEP_LAST:-$(get_config_value "$key")}"
    if [[ "${keep}" == "null" || "${keep}" == "-1" ]]; then continue; fi

    local patterns_str="${artifact_maps[$key]}"
    local all_items=()
    
    # Disable globbing temporarily to safely split patterns_str into individual patterns
    set -f
    # shellcheck disable=SC2206
    local patterns=($patterns_str)
    set +f

    for p in "${patterns[@]}"; do
      # Enable globbing for this specific expansion
      # shellcheck disable=SC2086
      for item in ${PROJECT_ROOT}/$p; do
        [[ -e "$item" ]] || continue
        all_items+=("$item")
      done
    done

    if [[ ${#all_items[@]} -gt 0 ]]; then
      # De-duplicate all_items
      IFS=$'\n' read -rd '' -a UNIQUE_ITEMS < <(printf "%s\n" "${all_items[@]}" | sort -u) || true
      
      if [[ ${#UNIQUE_ITEMS[@]} -gt $keep ]]; then
        # Sort items by modification time, newest first
        # We want to keep the N newest, so we delete the (Total - N) oldest.
        local sorted_items
        sorted_items=$(ls -dt "${UNIQUE_ITEMS[@]}" | tail -n +$((keep + 1)))
        while IFS= read -r item; do
          [[ -n "$item" ]] && CANDIDATES+=("$item")
        done <<< "$sorted_items"
      fi
    fi
  done
}

# --- SECTION: BACKUPS ---
clean_backups() {
  local keep="${KEEP_LAST:-$(get_config_value "backups_keep_last")}"
  if [[ "${keep}" == "null" || "${keep}" == "-1" ]]; then return 0; fi

  local backup_dirs=(
    "${PROJECT_ROOT}/artifacts/backups"
    "${PROJECT_ROOT}/artifacts/backups-local"
  )

  for bdir in "${backup_dirs[@]}"; do
    [[ -d "$bdir" ]] || continue
    local items=()
    for item in "$bdir"/*; do
      [[ -e "$item" ]] || continue
      items+=("$item")
    done

    if [[ ${#items[@]} -gt 0 ]]; then
      # De-duplicate
      IFS=$'\n' read -rd '' -a UNIQUE_ITEMS < <(printf "%s\n" "${items[@]}" | sort -u) || true
      
      if [[ ${#UNIQUE_ITEMS[@]} -gt $keep ]]; then
        local sorted_items
        sorted_items=$(ls -dt "${UNIQUE_ITEMS[@]}" | tail -n +$((keep + 1)))
        while IFS= read -r item; do
          [[ -n "$item" ]] && CANDIDATES+=("$item")
        done <<< "$sorted_items"
      fi
    fi
  done
}

# --- MAIN EXECUTION ---

case "${SECTION}" in
  rag) clean_rag ;;
  tts) clean_tts ;;
  logs) clean_logs ;;
  artifacts) clean_artifacts ;;
  backups) clean_backups ;;
  all)
    clean_rag
    clean_tts
    clean_logs
    clean_artifacts
    # Backups only in 'all' if not explicitly excluded or if we want to follow the 'all' rule
    clean_backups
    ;;
  *) echo "Unknown section: ${SECTION}"; exit 1 ;;
esac

# De-duplicate candidates and filter protected
FINAL_CANDIDATES=()
if [[ ${#CANDIDATES[@]} -gt 0 ]]; then
  # Use sort -u to de-duplicate
  IFS=$'\n' read -rd '' -a UNIQUE_CANDIDATES < <(printf "%s\n" "${CANDIDATES[@]}" | sort -u) || true
  for c in "${UNIQUE_CANDIDATES[@]}"; do
    if is_protected "$c"; then
      SKIPPED+=("$c")
    else
      FINAL_CANDIDATES+=("$c")
    fi
  done
fi

if [[ ${#FINAL_CANDIDATES[@]} -eq 0 ]]; then
  echo "No candidates found for deletion in section ${SECTION}."
else
  echo "Candidates for deletion:"
  for c in "${FINAL_CANDIDATES[@]}"; do
    echo "  - $c"
  done
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo ""
  echo "DRY RUN: No files were deleted."
  MODE="dry-run"
elif [[ "${YES}" == "false" ]]; then
  echo ""
  read -p "Are you sure you want to delete these ${#FINAL_CANDIDATES[@]} items? (y/N): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
  MODE="execute"
else
  MODE="execute"
fi

if [[ "${MODE}" == "execute" ]]; then
  for c in "${FINAL_CANDIDATES[@]}"; do
    if rm -rf "$c"; then
      echo "Deleted: $c"
      DELETED+=("$c")
    else
      log_error "Failed to delete: $c"
    fi
  done
fi

# Generate JSON Report
cat <<EOF > "${REPORT_JSON_FILE}"
{
  "timestamp": "${TIMESTAMP}",
  "mode": "${MODE}",
  "section": "${SECTION}",
  "config": {
    "path": "${CONFIG_PATH}",
    "older_than_days": "${OLDER_THAN_DAYS}",
    "keep_last": "${KEEP_LAST}",
    "client_id": "${CLIENT_ID}"
  },
  "summary": {
    "candidates": ${#FINAL_CANDIDATES[@]},
    "deleted": ${#DELETED[@]},
    "skipped": ${#SKIPPED[@]},
    "warnings": ${#WARNINGS[@]},
    "errors": ${#ERRORS[@]}
  },
  "candidates": $(printf '%s\n' "${FINAL_CANDIDATES[@]}" | jq -R . | jq -s .),
  "deleted": $(printf '%s\n' "${DELETED[@]}" | jq -R . | jq -s .),
  "skipped": $(printf '%s\n' "${SKIPPED[@]}" | jq -R . | jq -s .),
  "protected_paths": $(printf '%s\n' "${PROTECTED_PATHS[@]}" | jq -R . | jq -s .),
  "warnings": $(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .),
  "errors": $(printf '%s\n' "${ERRORS[@]}" | jq -R . | jq -s .),
  "project_root": "${PROJECT_ROOT}"
}
EOF

# Generate MD Report
cat <<EOF > "${REPORT_MD_FILE}"
# Retention Report - ${TIMESTAMP}

- **Mode:** ${MODE}
- **Section:** ${SECTION}
- **Project Root:** \`${PROJECT_ROOT}\`

## Summary
- **Candidates:** ${#FINAL_CANDIDATES[@]}
- **Deleted:** ${#DELETED[@]}
- **Skipped (Protected):** ${#SKIPPED[@]}
- **Warnings:** ${#WARNINGS[@]}
- **Errors:** ${#ERRORS[@]}

## Candidates
$(for c in "${FINAL_CANDIDATES[@]}"; do echo "- \`$c\`"; done)

## Deleted
$(for d in "${DELETED[@]}"; do echo "- \`$d\`"; done)

## Skipped (Protected)
$(for s in "${SKIPPED[@]}"; do echo "- \`$s\`"; done)

EOF

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
cat <<EOF >> "${REPORT_MD_FILE}"
## Warnings
$(for w in "${WARNINGS[@]}"; do echo "- $w"; done)
EOF
fi

if [[ ${#ERRORS[@]} -gt 0 ]]; then
cat <<EOF >> "${REPORT_MD_FILE}"
## Errors
$(for e in "${ERRORS[@]}"; do echo "- $e"; done)
EOF
fi

echo ""
echo "Report generated at:"
echo "  JSON: ${REPORT_JSON_FILE}"
echo "  MD:   ${REPORT_MD_FILE}"
