#!/bin/bash
# scripts/preflight-hermetic.sh
# Hermetic CLI tool and environment validation

set -e

REPORT_DIR="artifacts/preflight/latest"
REPORT_FILE="$REPORT_DIR/environment.md"
mkdir -p "$REPORT_DIR"

echo "# Environment Preflight Report" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Tool | Status | Version |" >> "$REPORT_FILE"
echo "| --- | --- | --- |" >> "$REPORT_FILE"

FAILED_TOOLS=0

check_tool() {
    local name=$1
    local cmd=$2
    local version_cmd=$3
    
    if command -v "$cmd" &> /dev/null; then
        local version=$($version_cmd 2>&1 | head -n 1)
        echo "✅ $name: Found ($version)"
        echo "| $name | ✅ PASS | $version |" >> "$REPORT_FILE"
    else
        echo "❌ $name: NOT FOUND"
        echo "| $name | ❌ FAIL | Not found |" >> "$REPORT_FILE"
        FAILED_TOOLS=$((FAILED_TOOLS + 1))
    fi
}

echo "Running hermetic preflight check..."

check_tool "Curl" "curl" "curl --version"
check_tool "Docker" "docker" "docker --version"
check_tool "Docker Compose" "docker-compose" "docker-compose --version"
check_tool "Python" "python3" "python3 --version"
check_tool "Node" "node" "node --version"
check_tool "NPM" "npm" "npm --version"

echo "" >> "$REPORT_FILE"
echo "## System Resources" >> "$REPORT_FILE"

# Disk Space
DISK_FREE=$(df -h . | awk 'NR==2 {print $4}')
echo "Disk Space Free: $DISK_FREE"
echo "- Disk Free: $DISK_FREE" >> "$REPORT_FILE"

# Permissions
if [ -w "." ]; then
    echo "✅ Permissions: Writable"
    echo "- Directory Writable: ✅ PASS" >> "$REPORT_FILE"
else
    echo "❌ Permissions: NOT WRITABLE"
    echo "- Directory Writable: ❌ FAIL" >> "$REPORT_FILE"
    FAILED_TOOLS=$((FAILED_TOOLS + 1))
fi

if [ $FAILED_TOOLS -gt 0 ]; then
    echo "=========================================================="
    echo "❌ PREFLIGHT FAILED: $FAILED_TOOLS issues detected."
    echo "Check $REPORT_FILE for details."
    echo "=========================================================="
    exit 1
else
    echo "=========================================================="
    echo "✅ PREFLIGHT PASSED: Environment is ready."
    echo "=========================================================="
    exit 0
fi
