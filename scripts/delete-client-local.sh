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
DRY_RUN=false
YES=false
REQUIRE_EXPORT=false
EXPORT_DIR="${ROOT_DIR}/exports/clients"
DELETE_RAG_FILES=false
DELETE_TTS_FILES=false
DELETE_INVOICES=false
ANONYMIZE_INSTEAD=false
ALLOW_DEMO_CLIENT=false

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --client-id UUID      Client ID to delete"
    echo "  --email EMAIL         Client Email to delete (will resolve to ID)"
    echo "  --dry-run             Show what would be done without performing actions"
    echo "  --yes                 Skip interactive confirmation (DANGEROUS)"
    echo "  --require-export      Ensure a recent export exists before deletion"
    echo "  --export-dir DIR      Directory to check/create exports (default: exports/clients)"
    echo "  --delete-rag-files    Physically remove RAG files from disk"
    echo "  --delete-tts-files    Physically remove TTS audio files from disk"
    echo "  --delete-invoices     Remove invoices from database (default: preserve/anonymize)"
    echo "  --anonymize-instead   Keep records but remove PII (overrides --delete-invoices false)"
    echo "  --allow-demo-client   Allow purging demo/special clients"
    echo "  --help                Show this help"
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --client-id) CLIENT_ID="$2"; shift ;;
        --email) EMAIL="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        --yes) YES=true ;;
        --require-export) REQUIRE_EXPORT=true ;;
        --export-dir) EXPORT_DIR="$2"; shift ;;
        --delete-rag-files) DELETE_RAG_FILES=true ;;
        --delete-tts-files) DELETE_TTS_FILES=true ;;
        --delete-invoices) DELETE_INVOICES=true ;;
        --anonymize-instead) ANONYMIZE_INSTEAD=true ;;
        --allow-demo-client) ALLOW_DEMO_CLIENT=true ;;
        --help) usage ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

if [[ -z "${CLIENT_ID}" && -z "${EMAIL}" ]]; then
    echo "Error: --client-id or --email is required"
    exit 1
fi

ADMIN_TOKEN="${ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
    echo "Error: ADMIN_TOKEN is required"
    exit 1
fi

BASE_URL="${BASE_URL:-$(default_base_url)}"
if [[ -f "/.dockerenv" && "${BASE_URL}" == "http://localhost:${HOST_PORT:-18080}" ]]; then
    BASE_URL="http://host.docker.internal:${HOST_PORT:-18080}"
fi

# Resolve Client ID and Name
echo "Resolving client info..."
CLIENTS_JSON="$(curl_base_url "${BASE_URL}/admin/clients" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")"

if [[ -n "${EMAIL}" ]]; then
    # Resolve ID from email/name
    CLIENT_ID=$(echo "${CLIENTS_JSON}" | python3 -c "import sys, json; 
clients = json.load(sys.stdin)
found = [c for c in clients if c['name'] == sys.argv[1]]
if not found:
    # Try metadata email
    found = [c for c in clients if c.get('metadata_json') and sys.argv[1] in c['metadata_json']]
if found: print(found[0]['id'])
" "${EMAIL}")
    
    if [[ -z "${CLIENT_ID}" ]]; then
        echo "Error: Could not find client with email/name '${EMAIL}'"
        exit 1
    fi
fi

if [[ -z "${CLIENT_ID}" ]]; then
    echo "Error: Client ID resolution failed"
    exit 1
fi

CLIENT_INFO=$(echo "${CLIENTS_JSON}" | python3 -c "import sys, json; 
clients = json.load(sys.stdin)
found = [c for c in clients if c['id'] == sys.argv[1]]
if found: print(json.dumps(found[0]))
" "${CLIENT_ID}")

if [[ -z "${CLIENT_INFO}" ]]; then
    echo "Error: Client ID '${CLIENT_ID}' not found"
    exit 1
fi

CLIENT_NAME=$(echo "${CLIENT_INFO}" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")

# Safety checks
if [[ "${CLIENT_NAME}" == "demo-client" && "${ALLOW_DEMO_CLIENT}" != "true" ]]; then
    echo "Error: '${CLIENT_NAME}' is a demo client. Use --allow-demo-client to proceed."
    exit 1
fi

# Check Export
if [[ "${REQUIRE_EXPORT}" == "true" ]]; then
    echo "Checking for recent export in ${EXPORT_DIR}/${CLIENT_ID}..."
    # We always create a new one to be safe if required
    echo "Requirement --require-export met: Creating fresh export..."
    "${SCRIPT_DIR}/export-client-local.sh" --client-id "${CLIENT_ID}" --include-rag-files --include-tts-files
fi

# Dry Run Report
if [[ "${DRY_RUN}" == "true" ]]; then
    echo "---------------------------------------------------"
    echo "--- DRY RUN REPORT ---"
    echo "Client: ${CLIENT_NAME} (${CLIENT_ID})"
    echo "Mode: $(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "ANONYMIZE"; else echo "PURGE"; fi)"
    echo "Database Actions:"
    echo "  - Revoke API keys: YES"
    echo "  - Delete Usage records: $(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "NO (Anonymized)"; else echo "YES"; fi)"
    echo "  - Delete Invoices: ${DELETE_INVOICES}"
    echo "  - Delete RAG metadata: ${DELETE_RAG_FILES}"
    echo "  - Delete TTS metadata: ${DELETE_TTS_FILES}"
    echo "  - Delete Audit events: false (preserved by default)"
    echo "File System Actions:"
    echo "  - Delete RAG files: ${DELETE_RAG_FILES} ($(if [[ "${DELETE_RAG_FILES}" == "true" ]]; then echo "${ROOT_DIR}/data/rag_uploads/${CLIENT_ID}"; else echo "N/A"; fi))"
    echo "  - Delete TTS files: ${DELETE_TTS_FILES} ($(if [[ "${DELETE_TTS_FILES}" == "true" ]]; then echo "find data/ -name *${CLIENT_ID}*.wav"; else echo "N/A"; fi))"
    echo "Safety Status:"
    echo "  - Is Demo Client: $(if [[ "${CLIENT_NAME}" == "demo-client" ]]; then echo "YES (Protected)"; else echo "NO"; fi)"
    echo "  - Models/Releases protection: ACTIVE"
    echo "---------------------------------------------------"
    exit 0
fi

# Confirmation
if [[ "${YES}" != "true" ]]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "WARNING: You are about to permanently DELETE or ANONYMIZE client data."
    echo "Client: ${CLIENT_NAME} (${CLIENT_ID})"
    echo "Mode: $(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "ANONYMIZE"; else echo "PURGE"; fi)"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "To proceed, type exactly: DELETE CLIENT ${CLIENT_ID}"
    read -r -p "> " CONFIRM
    if [[ "${CONFIRM}" != "DELETE CLIENT ${CLIENT_ID}" ]]; then
        echo "Aborted. Confirmation mismatch."
        exit 1
    fi
fi

# Perform Purge
echo "Calling Purge API..."
PURGE_PAYLOAD=$(cat <<EOF
{
  "anonymize_instead": ${ANONYMIZE_INSTEAD},
  "delete_invoices": ${DELETE_INVOICES},
  "delete_usage": $(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "false"; else echo "true"; fi),
  "delete_rag_metadata": ${DELETE_RAG_FILES},
  "delete_tts_metadata": ${DELETE_TTS_FILES},
  "allow_demo_client": ${ALLOW_DEMO_CLIENT}
}
EOF
)

curl_base_url "${BASE_URL}/admin/clients/${CLIENT_ID}/purge" -fsS -X POST \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${PURGE_PAYLOAD}"

# Handle Physical Files
TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
REPORT_DIR="${ROOT_DIR}/artifacts/client-deletions/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

DELETED_FILES=()

if [[ "${DELETE_RAG_FILES}" == "true" ]]; then
    # Protect against empty CLIENT_ID or root deletion
    if [[ -n "${CLIENT_ID}" && "${CLIENT_ID}" != "/" ]]; then
        RAG_DIR="${ROOT_DIR}/data/rag_uploads/${CLIENT_ID}"
        if [[ -d "${RAG_DIR}" ]]; then
            echo "Removing RAG files from ${RAG_DIR}..."
            # Use find to list before removing for report
            while IFS= read -r f; do DELETED_FILES+=("$f"); done < <(find "${RAG_DIR}" -type f)
            rm -rf "${RAG_DIR}"
        fi
    fi
fi

if [[ "${DELETE_TTS_FILES}" == "true" ]]; then
    echo "Searching and removing TTS files..."
    while IFS= read -r f; do
        if [[ -f "$f" ]]; then
            echo "Removing $f"
            DELETED_FILES+=("$f")
            rm "$f"
        fi
    done < <(find "${ROOT_DIR}/data" "${ROOT_DIR}/artifacts" -name "*${CLIENT_ID}*.wav" 2>/dev/null || true)
fi

# Generate Report
cat <<EOF > "${REPORT_DIR}/delete-report.json"
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "client_id": "${CLIENT_ID}",
  "client_name": "${CLIENT_NAME}",
  "action_type": "$(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "anonymize"; else echo "purge"; fi)",
  "options": {
    "anonymize_instead": ${ANONYMIZE_INSTEAD},
    "delete_invoices": ${DELETE_INVOICES},
    "delete_rag_files": ${DELETE_RAG_FILES},
    "delete_tts_files": ${DELETE_TTS_FILES},
    "require_export": ${REQUIRE_EXPORT}
  },
  "deleted_physical_files": $(printf '%s\n' "${DELETED_FILES[@]}" | python3 -c "import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")
}
EOF

echo "---------------------------------------------------"
echo "Success! Client offboarding completed."
echo "Mode: $(if [[ "${ANONYMIZE_INSTEAD}" == "true" ]]; then echo "Anonymized"; else echo "Purged"; fi)"
echo "Report generated at ${REPORT_DIR}/delete-report.json"
echo "---------------------------------------------------"
