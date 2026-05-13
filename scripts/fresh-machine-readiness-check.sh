#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DRY_RUN=false
JSON_OUTPUT=false
OUTPUT_DIR="${ROOT_DIR}/artifacts/fresh-machine-check"
HELP=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
RESULTS=()
DETAILS=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Check if the current machine is ready for a fresh installation of LLM Inference Stack.

Options:
  --dry-run        Run in checklist/dry-run mode (no destructive operations)
  --json           Output results as JSON
  --output-dir DIR Directory for output artifacts (default: artifacts/fresh-machine-check)
  --help           Show this help message
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --json) JSON_OUTPUT=true ;;
        --output-dir) OUTPUT_DIR="$2"; shift ;;
        --help) HELP=true ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
    shift
done

$HELP && usage

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

check() {
    local check_name="$1"
    local status="$2"
    local detail="$3"
    RESULTS+=("${status}|${check_name}|${detail}")
    case "$status" in
        PASS) ((PASS++)) ;;
        FAIL) ((FAIL++)) ;;
        WARN) ((WARN++)) ;;
    esac
    DETAILS+=("$(printf '  %-8s %-50s %s' "${status}" "${check_name}" "${detail}")")
}

echo ""
echo "=============================================="
echo "  Fresh Machine Readiness Check"
echo "  Timestamp: ${TIMESTAMP}"
echo "=============================================="

# 1. OS detection
os_name="$(uname -s)"
if [[ "${os_name}" == "Linux" ]]; then
    check "OS (Linux)" "PASS" "Linux detected"
elif [[ "${os_name}" == Darwin ]]; then
    check "OS (Linux)" "FAIL" "macOS detected - Linux/WSL2 required"
else
    check "OS (Linux)" "FAIL" "${os_name} detected - Linux/WSL2 required"
fi

# 2. WSL2 detection
if grep -qi microsoft /proc/version 2>/dev/null; then
    WSL_VERSION=$(wsl.exe --version 2>/dev/null | grep -oP 'WSL version \K[0-9.]+' || echo "unknown")
    check "WSL2" "PASS" "WSL2 detected (version ${WSL_VERSION})"
else
    check "WSL2" "PASS" "Native Linux (WSL2 check skipped)"
fi

# 3. Docker
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown")
    check "Docker" "PASS" "Docker ${DOCKER_VER}"
else
    check "Docker" "FAIL" "docker command not found"
fi

# 4. Docker daemon
if docker info &>/dev/null; then
    check "Docker daemon" "PASS" "Docker daemon is running"
else
    check "Docker daemon" "FAIL" "Docker daemon not reachable"
fi

# 5. docker compose
if docker compose version &>/dev/null; then
    DC_VER=$(docker compose version --short 2>/dev/null || echo "unknown")
    check "docker compose" "PASS" "docker compose ${DC_VER}"
else
    check "docker compose" "FAIL" "docker compose plugin not found"
fi

# 6. git
if command -v git &>/dev/null; then
    GIT_VER=$(git --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown")
    check "git" "PASS" "git ${GIT_VER}"
else
    check "git" "FAIL" "git not found"
fi

# 7. curl
if command -v curl &>/dev/null; then
    check "curl" "PASS" "$(curl --version | head -1)"
else
    check "curl" "FAIL" "curl not found"
fi

# 8. jq
if command -v jq &>/dev/null; then
    JQ_VER=$(jq --version 2>/dev/null || echo "unknown")
    check "jq" "PASS" "${JQ_VER}"
else
    check "jq" "FAIL" "jq not found"
fi

# 9. python3
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>/dev/null || echo "unknown")
    check "python3" "PASS" "${PY_VER}"
else
    check "python3" "FAIL" "python3 not found"
fi

# 10. Disk space
if command -v df &>/dev/null; then
    DISK_AVAIL=$(df -BG "$(dirname "${ROOT_DIR}")" 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ -n "${DISK_AVAIL}" && "${DISK_AVAIL}" -ge 10 ]]; then
        check "Disk space (>=10GB)" "PASS" "${DISK_AVAIL}GB available"
    elif [[ -n "${DISK_AVAIL}" ]]; then
        check "Disk space (>=10GB)" "FAIL" "${DISK_AVAIL}GB available (minimum 10GB)"
    else
        check "Disk space (>=10GB)" "WARN" "Could not determine free space"
    fi
else
    check "Disk space (>=10GB)" "WARN" "df not available"
fi

# 11. Available RAM
if command -v free &>/dev/null; then
    RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/ {print $2}')
    if [[ -n "${RAM_GB}" && "${RAM_GB}" -ge 4 ]]; then
        check "RAM (>=4GB)" "PASS" "${RAM_GB}GB total"
    elif [[ -n "${RAM_GB}" ]]; then
        check "RAM (>=4GB)" "FAIL" "${RAM_GB}GB total (minimum 4GB)"
    else
        check "RAM (>=4GB)" "WARN" "Could not determine RAM"
    fi
else
    check "RAM (>=4GB)" "WARN" "free not available"
fi

# 12. nvidia-smi (optional)
if command -v nvidia-smi &>/dev/null; then
    NVIDIA_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    check "NVIDIA GPU (optional)" "PASS" "${NVIDIA_INFO}"
else
    check "NVIDIA GPU (optional)" "WARN" "nvidia-smi not found (CPU-only mode)"
fi

# 13. Free ports
for port in 18080 5432 6379; do
    if command -v ss &>/dev/null; then
        if ss -tlnp "sport = :${port}" 2>/dev/null | grep -q LISTEN; then
            check "Port ${port} free" "FAIL" "Port ${port} is in use"
        else
            check "Port ${port} free" "PASS" "Port ${port} is available"
        fi
    elif command -v netstat &>/dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
            check "Port ${port} free" "FAIL" "Port ${port} is in use"
        else
            check "Port ${port} free" "PASS" "Port ${port} is available"
        fi
    else
        check "Port ${port} free" "WARN" "Cannot check port (ss/netstat not available)"
    fi
done

# 14. Script permissions
UNEXECUTABLE=$(find "${ROOT_DIR}/scripts" -maxdepth 1 -name '*.sh' ! -executable 2>/dev/null | head -5)
if [[ -z "${UNEXECUTABLE}" ]]; then
    check "Script permissions" "PASS" "All .sh scripts are executable"
else
    check "Script permissions" "WARN" "Some scripts lack +x"
fi

# 15. .env.local exists
if [[ -f "${ROOT_DIR}/.env.local" ]]; then
    check ".env.local exists" "PASS" "Found .env.local"
elif [[ -f "${ROOT_DIR}/.env" ]]; then
    check ".env.local exists" "WARN" "Using .env instead of .env.local"
else
    check ".env.local exists" "FAIL" ".env.local not found (hint: cp .env.example .env.local)"
fi

# 16. Model file or mock mode
MOCK_MODE=false
if [[ -f "${ROOT_DIR}/.env.local" ]] && grep -qi "MODEL_MOCK_MODE=true" "${ROOT_DIR}/.env.local" 2>/dev/null; then
    MOCK_MODE=true
fi
if [[ -f "${ROOT_DIR}/.env" ]] && grep -qi "MODEL_MOCK_MODE=true" "${ROOT_DIR}/.env" 2>/dev/null; then
    MOCK_MODE=true
fi

MODEL_COUNT=$(find "${ROOT_DIR}/models" -maxdepth 1 -name '*.gguf' 2>/dev/null | wc -l)
MODEL_COUNT=$((MODEL_COUNT + 0))
if [[ "${MODEL_COUNT}" -gt 0 ]]; then
    check "Model GGUF present" "PASS" "${MODEL_COUNT} GGUF file(s) in models/"
elif $MOCK_MODE; then
    check "Model GGUF present" "PASS" "No GGUF file, but MODEL_MOCK_MODE=true"
else
    check "Model GGUF present" "FAIL" "No GGUF file and MODEL_MOCK_MODE not set"
fi

# 17. .gitignore
CHECK_GITIGNORE=true
for pattern in '.env.*' '.env' 'models/' 'artifacts/' '*.gguf'; do
    if ! grep -q "${pattern}" "${ROOT_DIR}/.gitignore" 2>/dev/null; then
        check ".gitignore protects ${pattern}" "WARN" "${pattern} not in .gitignore"
        CHECK_GITIGNORE=false
    fi
done
if $CHECK_GITIGNORE; then
    check ".gitignore protects local files" "PASS" "All local patterns covered"
fi

# --------------- REPORT ---------------
echo ""
echo "--- Results ---"
for d in "${DETAILS[@]}"; do
    case "${d}" in
        "  PASS"*) echo -e "${GREEN}${d}${NC}" ;;
        "  FAIL"*) echo -e "${RED}${d}${NC}" ;;
        "  WARN"*) echo -e "${YELLOW}${d}${NC}" ;;
        *) echo "${d}" ;;
    esac
done
echo ""
echo -e "  ${GREEN}PASS: ${PASS}${NC} | ${RED}FAIL: ${FAIL}${NC} | ${YELLOW}WARN: ${WARN}${NC} | Total: $((PASS+FAIL+WARN))"
echo "=============================================="

# Generate JSON and MD reports
json_file="${REPORT_DIR}/fresh-machine-check.json"
md_file="${REPORT_DIR}/fresh-machine-check.md"
_first=true

{
    echo "["
    for _r in "${RESULTS[@]}"; do
        if $_first; then _first=false; else echo ","; fi
        _status="${_r%%|*}"
        _rest="${_r#*|}"
        _name="${_rest%%|*}"
        _detail="${_rest#*|}"
        echo "  {\"check\": \"${_name}\", \"status\": \"${_status}\", \"detail\": \"${_detail}\"}"
    done
    echo ""
    echo "]"
} > "${json_file}"

{
    echo "# Fresh Machine Readiness Check Report"
    echo ""
    echo "**Timestamp:** ${TIMESTAMP}"
    echo ""
    echo "## Summary"
    echo ""
    echo "| Status | Count |"
    echo "|--------|-------|"
    echo "| PASS   | ${PASS} |"
    echo "| FAIL   | ${FAIL} |"
    echo "| WARN   | ${WARN} |"
    echo "| **Total** | **$((PASS+FAIL+WARN))** |"
    echo ""
    echo "## Detailed Results"
    echo ""
    echo "| Status | Check | Detail |"
    echo "|--------|-------|--------|"
    for _r in "${RESULTS[@]}"; do
        _status="${_r%%|*}"
        _rest="${_r#*|}"
        _name="${_rest%%|*}"
        _detail="${_rest#*|}"
        echo "| ${_status} | ${_name} | ${_detail} |"
    done
} > "${md_file}"

echo ""
echo "Reports generated:"
echo "  JSON: ${json_file}"
echo "  MD:   ${md_file}"

if [[ "${FAIL}" -gt 0 ]]; then
    exit 1
fi
exit 0
