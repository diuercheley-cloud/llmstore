#!/usr/bin/env bash
set -euo pipefail

# scripts/redact-local-sensitive-artifacts.sh
# Redacts sensitive information from local generated artifacts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/redaction.sh"

CHECK_PATH="${ROOT_DIR}/artifacts"
IN_PLACE=false
DRY_RUN=false
REDACTION_COUNT=0

usage() {
    echo "Usage: $0 [--path <path>] [--in-place] [--dry-run]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --path) CHECK_PATH="$2"; shift 2 ;;
        --in-place) IN_PLACE=true; shift 1 ;;
        --dry-run) DRY_RUN=true; shift 1 ;;
        *) usage ;;
    esac
done

if [[ ! -e "${CHECK_PATH}" ]]; then
    echo "Error: Path ${CHECK_PATH} does not exist."
    exit 1
fi

echo "Scanning for sensitive data in: ${CHECK_PATH}"

process_file() {
    local file="$1"
    local extension="${file##*.}"
    
    if [[ "${extension}" == "json" ]]; then
        if [[ "${DRY_RUN}" == "true" ]]; then
            local diff_count
            diff_count=$("${ROOT_DIR}/scripts/redact_json.py" "$file" | diff "$file" - | grep -c "^[<>]" || true)
            if [[ $diff_count -gt 0 ]]; then
                echo "[DRY-RUN] Found sensitive data in JSON: ${file}"
                REDACTION_COUNT=$((REDACTION_COUNT + 1))
            fi
        elif [[ "${IN_PLACE}" == "true" ]]; then
            local original_md5
            original_md5=$(md5sum "$file" | awk '{print $1}')
            "${ROOT_DIR}/scripts/redact_json.py" --inplace --file "$file"
            local new_md5
            new_md5=$(md5sum "$file" | awk '{print $1}')
            if [[ "${original_md5}" != "${new_md5}" ]]; then
                echo "Redacted JSON: ${file}"
                REDACTION_COUNT=$((REDACTION_COUNT + 1))
            fi
        else
            "${ROOT_DIR}/scripts/redact_json.py" "$file"
        fi
    else
        if [[ "${DRY_RUN}" == "true" ]]; then
            local diff_count
            diff_count=$(redact_stream < "$file" | diff "$file" - | grep -c "^[<>]" || true)
            if [[ $diff_count -gt 0 ]]; then
                echo "[DRY-RUN] Found sensitive data in: ${file}"
                REDACTION_COUNT=$((REDACTION_COUNT + 1))
            fi
        elif [[ "${IN_PLACE}" == "true" ]]; then
            local original_md5
            original_md5=$(md5sum "$file" | awk '{print $1}')
            redact_file_inplace "$file"
            local new_md5
            new_md5=$(md5sum "$file" | awk '{print $1}')
            if [[ "${original_md5}" != "${new_md5}" ]]; then
                echo "Redacted: ${file}"
                REDACTION_COUNT=$((REDACTION_COUNT + 1))
            fi
        else
            redact_stream < "$file"
        fi
    fi
}

# Find files to process
if [[ -f "${CHECK_PATH}" ]]; then
    process_file "${CHECK_PATH}"
else
    while IFS= read -r file; do
        process_file "${file}"
    done < <(find "${CHECK_PATH}" -type f \( -name "*.md" -o -name "*.json" -o -name "*.log" -o -name "*.txt" \) | sort)
fi

echo "--------------------------------------------------"
if [[ "${DRY_RUN}" == "true" ]]; then
    echo "Dry-run complete. Files needing redaction: ${REDACTION_COUNT}"
else
    echo "Redaction complete. Files modified: ${REDACTION_COUNT}"
fi
