#!/bin/bash
# check-working-tree-governance.sh
# Governance check that distinguishes dirty_allowed_runtime from dirty_blocking.
set -euo pipefail

echo "=========================================="
echo "  Working Tree Governance Check"
echo "=========================================="

CONFIG_FILE="config/working-tree-governance.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found"
  exit 1
fi

ARTIFACT_DIR="${1:-artifacts/releases}"

# Parse allowed patterns from governance config
ALLOWED_ARTIFACTS_PATTERNS=$(grep -A100 'allowed_artifacts:' "$CONFIG_FILE" | grep '^\s*-\s' | sed 's/^\s*-\s*//' || true)
FORBIDDEN_RUNTIME=$(grep -A100 'forbidden_runtime_files:' "$CONFIG_FILE" | grep '^\s*-\s' | sed 's/^\s*-\s*//' || true)
FORBIDDEN_DEBUG=$(grep -A100 'forbidden_debug_files:' "$CONFIG_FILE" | grep '^\s*-\s' | sed 's/^\s*-\s*//' || true)
ALLOWED_LOCAL=$(grep -A100 'allowed_local_env:' "$CONFIG_FILE" | grep '^\s*-\s' | sed 's/^\s*-\s*//' || true)

dirty_blocking=0
blocking_reasons=""

# 1. Check for forbidden runtime files
while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  if ls $pattern 2>/dev/null | head -5 | grep -q .; then
    echo "BLOCKING: Forbidden runtime file pattern matched: $pattern"
    dirty_blocking=1
    blocking_reasons="$blocking_reasons\n  - forbidden_runtime: $pattern"
  fi
done <<< "$FORBIDDEN_RUNTIME"

# 2. Check for forbidden debug files
while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  if ls $pattern 2>/dev/null | head -5 | grep -q .; then
    echo "BLOCKING: Forbidden debug file pattern matched: $pattern"
    dirty_blocking=1
    blocking_reasons="$blocking_reasons\n  - forbidden_debug: $pattern"
  fi
done <<< "$FORBIDDEN_DEBUG"

# 3. Check git status for uncommitted changes
UNSTAGED=$(git status --short 2>/dev/null | wc -l)
if [ "$UNSTAGED" -gt 0 ]; then
  # Check if all unstaged changes match allowed patterns
  ALLOWED=true
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    status="${line:0:2}"
    file="${line:3}"

    # Check if file matches allowed artifacts
    MATCHED=false
    while IFS= read -r pattern; do
      [ -z "$pattern" ] && continue
      if [[ "$file" == $pattern ]]; then
        MATCHED=true
        break
      fi
    done <<< "$ALLOWED_ARTIFACTS_PATTERNS"

    if [ "$MATCHED" = false ]; then
      # Check if file matches allowed local env
      while IFS= read -r pattern; do
        [ -z "$pattern" ] && continue
        if [[ "$file" == $pattern ]]; then
          MATCHED=true
          break
        fi
      done <<< "$ALLOWED_LOCAL"

      if [ "$MATCHED" = false ]; then
        echo "BLOCKING: Unstaged change not in allowed patterns: $file"
        ALLOWED=false
        dirty_blocking=1
        blocking_reasons="$blocking_reasons\n  - unclassified_dirty: $file"
      fi
    fi
  done <<< "$(git status --short)"

  if [ "$ALLOWED" = true ]; then
    echo "Dirty but non-blocking: all unstaged changes are allowed artifacts"
  fi
fi

# 4. Check for secrets
if git ls-files --others --exclude-standard | grep -qiE '(\.key|\.pem|\.cert|secret|credential|token)' 2>/dev/null; then
  echo "BLOCKING: Potential secret files detected in untracked files"
  dirty_blocking=1
  blocking_reasons="$blocking_reasons\n  - secret_risk: untracked key/cert/secret files"
fi

# 5. Summary
echo ""
echo "=========================================="
echo "  Governance Check Result"
echo "=========================================="

if [ "$dirty_blocking" -eq 1 ]; then
  echo "  Status: DIRTY_BLOCKING"
  echo "  Reasons:$blocking_reasons"
  exit 1
elif [ "$UNSTAGED" -gt 0 ]; then
  echo "  Status: DIRTY_NON_BLOCKING (allowed artifacts only)"
  exit 0
else
  echo "  Status: CLEAN"
  exit 0
fi
