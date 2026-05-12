#!/usr/bin/env bash
# scripts/audit-root-files-local.sh
# Audits Python files in the repository root for usage and relocation potential.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="${ROOT_DIR}/artifacts/repo-cleanup/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

JSON_REPORT="${REPORT_DIR}/root-files-audit.json"
MD_REPORT="${REPORT_DIR}/root-files-audit.md"

echo "{\"timestamp\": \"${TIMESTAMP}\", \"files\": []}" > "${JSON_REPORT}"

cat <<EOF > "${MD_REPORT}"
# Root Files Audit Report - ${TIMESTAMP}

This report identifies Python files in the repository root and analyzes their usage to determine if they should be relocated.

## Audit Results

| File | Type | Referenced By | Suggested Action |
|------|------|---------------|------------------|
EOF

# Find all .py files in root (and __init__.py)
FILES=$(find "${ROOT_DIR}" -maxdepth 1 -name "*.py" -printf "%f\n" | sort)

for FILE in ${FILES}; do
    echo "Auditing ${FILE}..."
    
    # Detect if it's imported
    BASENAME=$(basename "${FILE}" .py)
    IMPORTS=$(grep -r "import ${BASENAME}" "${ROOT_DIR}" --exclude-dir=".venv" --exclude-dir=".git" --exclude-dir=".ruff_cache" --exclude-dir="artifacts" --exclude="${FILE}" || true)
    FROM_IMPORTS=$(grep -r "from ${BASENAME} import" "${ROOT_DIR}" --exclude-dir=".venv" --exclude-dir=".git" --exclude-dir=".ruff_cache" --exclude-dir="artifacts" --exclude="${FILE}" || true)
    
    # Detect direct calls in shell scripts
    CALLS=$(grep -r "${FILE}" "${ROOT_DIR}/scripts" --exclude-dir=".venv" --exclude-dir="artifacts" || true)
    
    # Detect Makefile references
    MAKEFILE_REFS=$(grep "${FILE}" "${ROOT_DIR}/Makefile" 2>/dev/null || true)
    
    # Detect Doc references
    DOC_REFS=$(grep -r "${FILE}" "${ROOT_DIR}/docs" --exclude-dir="artifacts" || true)

    # Determine type and suggested action
    TYPE="Utility/Script"
    ACTION="Move to scripts/"
    
    if [[ "${FILE}" == "__init__.py" ]]; then
        TYPE="Package Marker"
        ACTION="Remove if not needed"
    elif [[ "${FILE}" == "llm_stack_client.py" ]]; then
        TYPE="Library Client"
        ACTION="Keep in root or move to lib/"
    elif [[ "${FILE}" == "test_simulate.py" ]] || [[ "${FILE}" == "test-max-concurrency.py" ]]; then
        TYPE="Test Utility"
        ACTION="Move to tests/ or scripts/"
    fi

    # Append to MD
    REF_COUNT=0
    [[ -n "${IMPORTS}" ]] && REF_COUNT=$((REF_COUNT + 1))
    [[ -n "${FROM_IMPORTS}" ]] && REF_COUNT=$((REF_COUNT + 1))
    [[ -n "${CALLS}" ]] && REF_COUNT=$((REF_COUNT + 1))
    [[ -n "${MAKEFILE_REFS}" ]] && REF_COUNT=$((REF_COUNT + 1))
    [[ -n "${DOC_REFS}" ]] && REF_COUNT=$((REF_COUNT + 1))
    
    echo "| ${FILE} | ${TYPE} | ${REF_COUNT} references | ${ACTION} |" >> "${MD_REPORT}"

    # Update JSON (using temporary file and jq would be better but let's use a simple approach)
    # Actually, let's just use python to update the JSON at the end or build it properly.
done

echo "" >> "${MD_REPORT}"
echo "## Detailed References" >> "${MD_REPORT}"

for FILE in ${FILES}; do
    echo "### ${FILE}" >> "${MD_REPORT}"
    BASENAME=$(basename "${FILE}" .py)
    
    echo "#### Imports" >> "${MD_REPORT}"
    grep -r "import ${BASENAME}" "${ROOT_DIR}" --exclude-dir=".venv" --exclude-dir=".git" --exclude-dir=".ruff_cache" --exclude-dir="artifacts" --exclude="${FILE}" >> "${MD_REPORT}" || echo "None" >> "${MD_REPORT}"
    grep -r "from ${BASENAME} import" "${ROOT_DIR}" --exclude-dir=".venv" --exclude-dir=".git" --exclude-dir=".ruff_cache" --exclude-dir="artifacts" --exclude="${FILE}" >> "${MD_REPORT}" || true
    
    echo "#### Script Calls" >> "${MD_REPORT}"
    grep -r "${FILE}" "${ROOT_DIR}/scripts" --exclude-dir=".venv" --exclude-dir="artifacts" >> "${MD_REPORT}" || echo "None" >> "${MD_REPORT}"
    
    echo "#### Makefile References" >> "${MD_REPORT}"
    grep "${FILE}" "${ROOT_DIR}/Makefile" >> "${MD_REPORT}" 2>/dev/null || echo "None" >> "${MD_REPORT}"

    echo "#### Doc References" >> "${MD_REPORT}"
    grep -r "${FILE}" "${ROOT_DIR}/docs" --exclude-dir="artifacts" >> "${MD_REPORT}" || echo "None" >> "${MD_REPORT}"
done

# Finalize JSON with a simple python script to make it valid
python3 - <<PYEND
import json
import os
import glob
from pathlib import Path

root_dir = "${ROOT_DIR}"
files = sorted([f for f in os.listdir(root_dir) if f.endswith('.py')])
report = {
    "timestamp": "${TIMESTAMP}",
    "files": []
}

for f in files:
    path = Path(root_dir) / f
    basename = path.stem
    
    # This is a bit redundant but ensures JSON is correct
    report["files"].append({
        "name": f,
        "suggested_action": "Move to scripts/" if f != "llm_stack_client.py" and f != "__init__.py" else "Review",
        "references": []
    })

with open("${JSON_REPORT}", "w") as jf:
    json.dump(report, jf, indent=2)
PYEND

echo "Audit complete. Reports generated in ${REPORT_DIR}"
