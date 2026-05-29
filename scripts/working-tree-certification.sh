#!/bin/bash
# working-tree-certification.sh — Verifies that the working tree is clean and classified.

set -euo pipefail

TAG="${1:-current}"
REPORT_DIR="artifacts/releases/${TAG}"
REPORT_FILE="${REPORT_DIR}/working-tree-certification.md"

echo "🔍 Starting Working Tree Certification..."

mkdir -p "$REPORT_DIR"

STATUS="$(git status --porcelain)"
if [ -n "$STATUS" ]; then
    {
        echo "# Working Tree Certification"
        echo
        echo "**Status:** FAIL"
        echo
        echo "## Findings"
        echo '```'
        echo "$STATUS"
        echo '```'
    } > "$REPORT_FILE"
    echo "❌ FAILED: Working tree is not clean."
    echo "$STATUS"
    exit 1
fi

# 3. Verify audit file exists
AUDIT_FILE="artifacts/releases/current/working-tree-audit.md"
if [ ! -f "$AUDIT_FILE" ]; then
    echo "❌ FAILED: Working tree audit report not found at $AUDIT_FILE"
    exit 1
fi

{
    echo "# Working Tree Certification"
    echo
    echo "**Status:** PASS"
    echo
    echo "- Tag: ${TAG}"
    echo "- Audit file: ${AUDIT_FILE}"
    echo "- Git status: clean"
} > "$REPORT_FILE"

echo "✅ SUCCESS: Working tree is clean and certified."
echo "Hardened release line can be declared."
