#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

# Default values
CLIENT_ID=""
EMAIL=""
OUTPUT_BASE_DIR="${ROOT_DIR}/exports/clients"
INCLUDE_RAG=false
INCLUDE_TTS=false
DRY_RUN=false
# Respect EXPORT_REDACT_PII or default to true
REDACT="${EXPORT_REDACT_PII:-true}"

# Help function
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --client-id UUID      Client ID to export"
    echo "  --email EMAIL         Client Email to export"
    echo "  --output-dir DIR      Base output directory (default: exports/clients)"
    echo "  --include-rag-files   Include RAG documents"
    echo "  --include-tts-files   Include TTS audio files"
    echo "  --dry-run             Do not perform export, only show what would be done"
    echo "  --redact-secrets BOOL Redact secrets (default: true or EXPORT_REDACT_PII)"
    echo "  --help                Show this help"
    exit 1
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --client-id) CLIENT_ID="$2"; shift ;;
        --email) EMAIL="$2"; shift ;;
        --output-dir) OUTPUT_BASE_DIR="$2"; shift ;;
        --include-rag-files) INCLUDE_RAG=true ;;
        --include-tts-files) INCLUDE_TTS=true ;;
        --dry-run) DRY_RUN=true ;;
        --redact-secrets) REDACT="$2"; shift ;;
        --help) usage ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

# Validation
if [[ -z "${CLIENT_ID}" && -z "${EMAIL}" ]]; then
    echo "Error: --client-id or --email is required"
    exit 1
fi

ADMIN_TOKEN="${ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
    # Try to get from .env if not set
    if [[ -f "${ROOT_DIR}/.env" ]]; then
        ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" "${ROOT_DIR}/.env" | cut -d= -f2- || echo "")
    fi
fi

if [[ -z "${ADMIN_TOKEN}" ]]; then
    echo "Error: ADMIN_TOKEN is required"
    exit 1
fi

BASE_URL="${BASE_URL:-$(default_base_url)}"
if [[ -f "/.dockerenv" && "${BASE_URL}" == "http://localhost:${HOST_PORT:-18080}" ]]; then
    BASE_URL="http://host.docker.internal:${HOST_PORT:-18080}"
fi

# 1. Fetch data from API
echo "Fetching client data from ${BASE_URL}..."
URL="${BASE_URL}/admin/clients/export-data?"
if [[ -n "${CLIENT_ID}" ]]; then URL="${URL}client_id=${CLIENT_ID}&"; fi
if [[ -n "${EMAIL}" ]]; then URL="${URL}email=${EMAIL}&"; fi
URL="${URL}redact=${REDACT}"

EXPORT_JSON="$(curl_base_url "${URL}" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")"

# Extract Client ID if not provided
if [[ -z "${CLIENT_ID}" ]]; then
    CLIENT_ID=$(echo "${EXPORT_JSON}" | python3 -c "import sys, json; print(json.load(sys.stdin)['client']['id'])")
fi

TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
EXPORT_DIR="${OUTPUT_BASE_DIR}/${CLIENT_ID}/${TIMESTAMP}"

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[DRY RUN] Would create export at ${EXPORT_DIR}"
    CLIENT_NAME=$(echo "${EXPORT_JSON}" | python3 -c "import sys, json; print(json.load(sys.stdin)['client']['name'])")
    echo "[DRY RUN] Client: ${CLIENT_NAME}"
    echo "[DRY RUN] Redaction enabled: ${REDACT}"
    exit 0
fi

mkdir -p "${EXPORT_DIR}"

# 2. Identify TTS files for metadata
echo "Searching for TTS files to include in metadata..."
TTS_FILES_LIST=""
while IFS= read -r f; do
    if [[ -f "$f" ]]; then
        if [[ -n "${TTS_FILES_LIST}" ]]; then TTS_FILES_LIST="${TTS_FILES_LIST},"; fi
        TTS_FILES_LIST="${TTS_FILES_LIST}$f"
    fi
done < <(find "${ROOT_DIR}/data" "${ROOT_DIR}/artifacts" -name "*${CLIENT_ID}*.wav" 2>/dev/null || true)

# 3. Write client-export.json and 4. Generate summary
python3 - "${EXPORT_JSON}" "${EXPORT_DIR}" "${INCLUDE_RAG}" "${INCLUDE_TTS}" "${TTS_FILES_LIST}" <<'PY'
import sys, json, os
from pathlib import Path

data = json.loads(sys.argv[1])
export_dir = Path(sys.argv[2])
inc_rag = sys.argv[3].lower() == 'true'
inc_tts = sys.argv[4].lower() == 'true'
tts_files = sys.argv[5].split(',') if sys.argv[5] else []

# Populate TTS metadata from found files
data['tts'] = []
for f_path in tts_files:
    p = Path(f_path)
    data['tts'].append({
        "filename": p.name,
        "path_hint": str(p.relative_to(os.getcwd())) if os.getcwd() in str(p) else str(p),
        "size_bytes": p.stat().st_size,
        "created_at": os.path.getctime(f_path)
    })

# Ensure all mandatory fields exist
mandatory_fields = [
    "export_version", "generated_at", "client", "plan", 
    "api_keys", "usage", "invoices", "rag", "tts", 
    "audit_events", "redaction"
]
for field in mandatory_fields:
    if field not in data:
        data[field] = None if field == "plan" else []

# Add included_files as required by spec
data['included_files'] = {
    "rag": inc_rag,
    "tts": inc_tts
}

with open(export_dir / "client-export.json", "w") as f:
    json.dump(data, f, indent=2)

client = data['client']
plan = data['plan'] or {'name': 'N/A'}

summary = f"""# Client Export Summary

- **Client ID:** {client['id']}
- **Generated At:** {data['generated_at']}
- **Export Version:** {data['export_version']}

## Client Info
- **Name:** {client['name']}
- **Status:** {client['billing_status']}
- **Plan:** {plan['name']}
- **Created At:** {client['created_at']}

## Resources
- **API Keys:** {len(data['api_keys'])}
- **Invoices:** {len(data['invoices'])}
- **Usage Records:** {len(data['usage'])}
- **RAG Documents:** {len(data['rag'])}
- **TTS Files identified:** {len(data['tts'])}
- **Security Events:** {len(data['audit_events'])}

## Redaction
- **Applied:** {data['redaction'].get('applied', False)}
- **Fields:** {", ".join(data['redaction'].get('redacted_fields', []))}

## Included Files
- **RAG:** {inc_rag}
- **TTS:** {inc_tts}
"""

(export_dir / "client-export.md").write_text(summary)
PY

# 5. Copy RAG files
if [[ "${INCLUDE_RAG}" == "true" ]]; then
    echo "Checking for RAG files..."
    RAG_DIR="${ROOT_DIR}/data/rag_uploads/${CLIENT_ID}"
    if [[ -d "${RAG_DIR}" ]]; then
        echo "Copying RAG files from ${RAG_DIR}..."
        mkdir -p "${EXPORT_DIR}/rag-files"
        cp -r "${RAG_DIR}/"* "${EXPORT_DIR}/rag-files/"
    else
        echo "No RAG files found at ${RAG_DIR}"
    fi
fi

# 6. Copy TTS files
if [[ "${INCLUDE_TTS}" == "true" ]]; then
    echo "Checking for TTS files..."
    if [[ -n "${TTS_FILES_LIST}" ]]; then
        mkdir -p "${EXPORT_DIR}/tts-files"
        IFS=',' read -ra ADDR <<< "${TTS_FILES_LIST}"
        for i in "${ADDR[@]}"; do
            cp "$i" "${EXPORT_DIR}/tts-files/"
        done
        echo "Copied ${#ADDR[@]} TTS files."
    else
        echo "No TTS files found to copy."
    fi
fi

# 6. Generate manifest.json
cat <<EOF > "${EXPORT_DIR}/manifest.json"
{
  "client_id": "${CLIENT_ID}",
  "timestamp": "${TIMESTAMP}",
  "included_rag": ${INCLUDE_RAG},
  "included_tts": ${INCLUDE_TTS},
  "redacted": ${REDACT},
  "export_dir": "${EXPORT_DIR}"
}
EOF

# 7. Security Check
echo "Running security check on export folder..."
if ! "${SCRIPT_DIR}/check-secrets.sh" --path "${EXPORT_DIR}"; then
    echo "ERROR: Security check failed. Secrets detected in export!"
    mv "${EXPORT_DIR}" "${EXPORT_DIR}.unsafe"
    echo "Export marked as unsafe at ${EXPORT_DIR}.unsafe"
    exit 1
fi

echo "---------------------------------------------------"
echo "Export successful: ${EXPORT_DIR}"
echo "Manifest: ${EXPORT_DIR}/manifest.json"
echo "Redaction confirmation: Applied=${REDACT}"
if grep -q "^exports/" "${ROOT_DIR}/.gitignore"; then
    echo "Git confirmation: 'exports/' is correctly ignored in .gitignore"
else
    echo "WARNING: 'exports/' is NOT in .gitignore! Fix this immediately."
fi
echo "---------------------------------------------------"
