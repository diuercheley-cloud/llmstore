#!/bin/bash
# export-release-manifest.sh
# Gera o release manifest com snapshot completo para reproducibilidade.
set -euo pipefail

RELEASE_TAG="${1:-v2.x-agentic-consolidation-hardening}"
ARTIFACT_DIR="artifacts/releases/$RELEASE_TAG"
mkdir -p "$ARTIFACT_DIR"

echo "=========================================="
echo "  Exporting Release Manifest"
echo "  Release: $RELEASE_TAG"
echo "=========================================="

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Feature flags snapshot
FEATURE_FLAGS_SNAPSHOT=""
if [ -f config/feature-flags.yaml ]; then
  FEATURE_FLAGS_SNAPSHOT=$(grep -E '^\s+\w+:\s*(true|false)$' config/feature-flags.yaml | head -100 || echo "")
fi

# Enabled flags
ENABLED_FLAGS=$(echo "$FEATURE_FLAGS_SNAPSHOT" | grep ': true' | sed 's/^\s*//' || echo "none")

# Python dependencies
PYTHON_DEPS=""
if [ -f requirements.txt ]; then
  PYTHON_DEPS=$(cat requirements.txt | grep -v '^\s*#' | grep -v '^\s*$' | head -50 || echo "")
elif [ -f pyproject.toml ]; then
  PYTHON_DEPS=$(grep -A200 '\[project.dependencies\]' pyproject.toml | grep -E '^\s+\"' | head -50 || echo "")
fi

# Node dependencies
NODE_DEPS=""
if [ -f package.json ]; then
  NODE_DEPS=$(grep -E '"(react|express|next|axios|vue|@angular|@opencode)' package.json | head -20 || echo "")
fi

# Migration files
MIGRATIONS=$(ls -1 control_plane/alembic/versions/*.py 2>/dev/null | wc -l || echo "0")

# API surface snapshot
API_SURFACE=""
if [ -f config/api-surface.yaml ]; then
  API_SURFACE=$(grep -E '^\s+/\w+' config/api-surface.yaml | head -30 || echo "")
fi

# Supported surface snapshot
SUPPORTED_SURFACE=""
if [ -f config/supported-surface.yaml ]; then
  SUPPORTED_SURFACE=$(grep -E '^\s+capability:' config/supported-surface.yaml | head -20 || echo "")
fi

# Runtime providers
RUNTIME_PROVIDERS=""
if [ -f config/providers.yaml ]; then
  RUNTIME_PROVIDERS=$(grep -E '^\s+- name:' config/providers.yaml | sed 's/^\s*- name:\s*//' | head -20 || echo "")
fi

# Freeze rules
FREEZE_RULES=""
if [ -f config/platform-freeze-rules.json ]; then
  FREEZE_RULES=$(python3 -c "
import json
with open('config/platform-freeze-rules.json') as f:
    data = json.load(f)
rules = data.get('frozen_modules', data.get('rules', data.keys()))
print(json.dumps(list(rules)[:20], indent=2))
" 2>/dev/null || echo "{}")
fi

# Git tags and branches for context
GIT_TAGS=$(git tag --points-at HEAD 2>/dev/null | tr '\n' ' ' || echo "none")

# ---------------------------------------------------------------
# Generate manifest JSON
# ---------------------------------------------------------------
cat > "$ARTIFACT_DIR/release-manifest.json" << EOF
{
  "manifest_version": "1.0.0",
  "release": "$RELEASE_TAG",
  "timestamp": "$TIMESTAMP",
  "git": {
    "sha": "$GIT_SHA",
    "branch": "$GIT_BRANCH",
    "tags": "$GIT_TAGS"
  },
  "migrations": {
    "count": $MIGRATIONS,
    "directory": "control_plane/alembic/versions/"
  },
  "feature_flags": {
    "total": $(echo "$FEATURE_FLAGS_SNAPSHOT" | wc -l),
    "enabled": $(echo "$ENABLED_FLAGS" | wc -l),
    "enabled_list": [$(echo "$ENABLED_FLAGS" | sed 's/: true//' | sed 's/^[ \t]*//' | sed 's/^/"/; s/$/"/' | tr '\n' ',' | sed 's/,$//')]
  },
  "api_surface": {
    "endpoints": $(echo "$API_SURFACE" | wc -l),
    "config_file": "config/api-surface.yaml"
  },
  "supported_surface": {
    "capabilities": $(echo "$SUPPORTED_SURFACE" | wc -l),
    "config_file": "config/supported-surface.yaml"
  },
  "dependencies": {
    "python": "$(echo "$PYTHON_DEPS" | wc -l) packages",
    "node": "$(echo "$NODE_DEPS" | wc -l) packages"
  },
  "runtime_providers": [$(echo "$RUNTIME_PROVIDERS" | sed 's/.*/"&"/' | tr '\n' ',' | sed 's/,$//')],
  "freeze_rules": $FREEZE_RULES,
  "reproducibility": {
    "git_clean_required": true,
    "working_tree_state": "$(git status --porcelain | wc -l) dirty files",
    "artifacts": {
      "summary": "$ARTIFACT_DIR/summary.md",
      "validation": "$ARTIFACT_DIR/validation.md",
      "certification": "$ARTIFACT_DIR/working-tree-certification.md"
    }
  }
}
EOF

echo "Manifest written to $ARTIFACT_DIR/release-manifest.json"
echo "  Git SHA: $GIT_SHA"
echo "  Branch: $GIT_BRANCH"
echo "  Migrations: $MIGRATIONS"
echo "  Feature flags enabled: $(echo "$ENABLED_FLAGS" | wc -l)"
