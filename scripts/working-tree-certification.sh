#!/bin/bash
# working-tree-certification.sh — Verifies that the working tree is clean and classified.

set -e

echo "🔍 Starting Working Tree Certification..."

# 1. Check for untracked files
UNTRACKED=$(git ls-files --others --exclude-standard)
if [ -n "$UNTRACKED" ]; then
    echo "❌ FAILED: Untracked files found in working tree:"
    echo "$UNTRACKED"
    echo "Every file must be either committed, ignored via .gitignore, or classified in working-tree-audit.md"
    exit 1
fi

# 2. Check for unstaged changes
if ! git diff --quiet; then
    echo "❌ FAILED: Unstaged changes found in working tree."
    echo "Please stage or stash your changes before certification."
    exit 1
fi

# 3. Verify audit file exists
AUDIT_FILE="artifacts/releases/current/working-tree-audit.md"
if [ ! -f "$AUDIT_FILE" ]; then
    echo "❌ FAILED: Working tree audit report not found at $AUDIT_FILE"
    exit 1
fi

echo "✅ SUCCESS: Working tree is clean and certified."
echo "Hardened release line can be declared."
