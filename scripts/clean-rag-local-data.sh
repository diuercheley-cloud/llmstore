#!/usr/bin/env bash
# scripts/clean-rag-local-data.sh - Safe RAG data cleanup script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
if [[ -f "${SCRIPT_DIR}/common.sh" ]]; then
  source "${SCRIPT_DIR}/common.sh"
  init_stack_env
else
  echo "Error: common.sh not found in ${SCRIPT_DIR}"
  exit 1
fi

DRY_RUN=false
YES=false
OLDER_THAN_DAYS=""
CLIENT_ID=""
INCLUDE_ARTIFACTS=false
RESET_DB_METADATA=false

usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --dry-run             Show what would be deleted"
  echo "  --yes                 Execute without interactive prompt"
  echo "  --older-than-days N   Only delete files older than N days"
  echo "  --client-id UUID      Only delete data for specific client_id"
  echo "  --include-artifacts   Include temporary RAG artifacts in artifacts/"
  echo "  --reset-db-metadata   Clear RAG metadata from database (requires --yes)"
  echo "  --help                Show this help"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --yes) YES=true; shift ;;
    --older-than-days) OLDER_THAN_DAYS="$2"; shift 2 ;;
    --client-id) CLIENT_ID="$2"; shift 2 ;;
    --include-artifacts) INCLUDE_ARTIFACTS=true; shift ;;
    --reset-db-metadata) RESET_DB_METADATA=true; shift ;;
    --help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [[ "${RESET_DB_METADATA}" == "true" && "${YES}" == "false" ]]; then
  echo "Error: --reset-db-metadata requires --yes to prevent accidental data loss."
  exit 1
fi

# Protection: Resolve paths and check if inside project
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"

# Absolute safety checks
if [[ -z "${PROJECT_ROOT}" || "${PROJECT_ROOT}" == "/" ]]; then
  echo "Error: PROJECT_ROOT is empty or /. Aborting for safety."
  exit 1
fi

# Target collection
TARGETS=()

# 1. Main RAG uploads directory
if [[ -d "${DATA_DIR}/rag_uploads" ]]; then
  if [[ -n "${CLIENT_ID}" ]]; then
    if [[ -d "${DATA_DIR}/rag_uploads/${CLIENT_ID}" ]]; then
      TARGETS+=("${DATA_DIR}/rag_uploads/${CLIENT_ID}")
    fi
  else
    # We want to clear the content of rag_uploads, but keep the dir itself?
    # Actually, the user says "limpar data/rag_uploads/", usually it means all contents.
    for d in "${DATA_DIR}"/rag_uploads/*; do
      [[ -e "$d" ]] || continue
      TARGETS+=("$d")
    done
  fi
fi

# 2. Variant RAG directories (e.g. from DR tests)
for d in "${DATA_DIR}"/rag_uploads-*; do
  [[ -e "$d" ]] || continue
  if [[ -n "${CLIENT_ID}" ]]; then
    if [[ -d "$d/${CLIENT_ID}" ]]; then
      TARGETS+=("$d/${CLIENT_ID}")
    fi
  else
    TARGETS+=("$d")
  fi
done

# 3. Artifacts (optional)
if [[ "${INCLUDE_ARTIFACTS}" == "true" ]]; then
  if [[ -d "${ARTIFACTS_DIR}" ]]; then
    # Search for anything RAG related in artifacts
    # Using find to be more precise
    while IFS= read -r line; do
      [[ -n "$line" ]] && TARGETS+=("$line")
    done < <(find "${ARTIFACTS_DIR}" -maxdepth 2 -type d -name "*rag*" 2>/dev/null || true)
  fi
fi

# Filter by age if requested
FINAL_TARGETS=()
if [[ -n "${OLDER_THAN_DAYS}" ]]; then
  for t in "${TARGETS[@]}"; do
    if [[ -e "$t" ]]; then
      # Check if path itself is older than N days
      if [[ $(find "$t" -maxdepth 0 -mtime +"${OLDER_THAN_DAYS}") ]]; then
        FINAL_TARGETS+=("$t")
      fi
    fi
  done
else
  FINAL_TARGETS=("${TARGETS[@]}")
fi

if [[ ${#FINAL_TARGETS[@]} -eq 0 && "${RESET_DB_METADATA}" == "false" ]]; then
  echo "No RAG data found matching the criteria."
  exit 0
fi

# Summary
echo "The following RAG data will be DELETED:"
for t in "${FINAL_TARGETS[@]}"; do
  echo "  - $t"
done

if [[ "${RESET_DB_METADATA}" == "true" ]]; then
  echo "  - Database metadata: tables rag_documents, rag_document_chunks (TRUNCATE)"
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo ""
  echo "DRY RUN: No files were deleted."
  exit 0
fi

# Confirmation
if [[ "${YES}" == "false" ]]; then
  echo ""
  printf "WARNING: This will permanently delete the RAG data listed above.\n"
  printf "To proceed, type exactly 'DELETE LOCAL RAG DATA': "
  read -r confirmation
  if [[ "${confirmation}" != "DELETE LOCAL RAG DATA" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

# Execution
SUCCESS_COUNT=0
for t in "${FINAL_TARGETS[@]}"; do
  # Safety Check 1: Must be inside PROJECT_ROOT
  if [[ "$t" != "${PROJECT_ROOT}"/* ]]; then
    echo "Warning: Skipping path outside project scope: $t"
    continue
  fi

  # Safety Check 2: Explicitly protect critical directories
  case "$t" in
    *"models"*|*"scripts"*|*"docs"*|*"migrations"*|*"backups"*|*"releases"*)
      echo "Error: PROTECTED PATH detected: $t. Skipping."
      continue
      ;;
  esac

  # Safety Check 3: Do not delete .gguf files directly
  if [[ -f "$t" && "$t" == *.gguf ]]; then
     echo "Error: PROTECTED FILE (.gguf) detected: $t. Skipping."
     continue
  fi

  if ! rm -rf "$t" 2>/dev/null; then
    # Permission denied usually happens because files were created by docker as root
    if [[ "$t" == "${DATA_DIR}/"* ]] && dc ps control-plane 2>/dev/null | grep -q "Up"; then
       REL_PATH="${t#${DATA_DIR}/}"
       echo "Notice: Permission denied for $t. Attempting deletion via control-plane container..."
       if dc exec -T control-plane rm -rf "/data/${REL_PATH}"; then
         echo "Deleted via docker: $t"
         SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
       else
         echo "Error: Failed to delete $t even via docker."
       fi
    else
       echo "Error: Could not delete $t (Permission denied). Try running with sudo if necessary."
    fi
  else
    echo "Deleted: $t"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  fi
done

if [[ "${RESET_DB_METADATA}" == "true" ]]; then
  echo "Resetting RAG database metadata..."
  # Use dc (docker compose) from common.sh
  if dc ps postgres | grep -q "Up"; then
    dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "TRUNCATE TABLE rag_document_chunks, rag_documents CASCADE;"
    echo "Database metadata cleared."
  else
    echo "Warning: Postgres container is not running. Could not clear DB metadata."
  fi
fi

echo "Cleanup complete. ${SUCCESS_COUNT} items removed."
