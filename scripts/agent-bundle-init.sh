#!/usr/bin/env bash
# agent-bundle-init.sh — Create agent bundle skeleton
set -euo pipefail

BUNDLE_NAME="${1:-my-agent}"
BUNDLE_DIR="${2:-$BUNDLE_NAME}"

if [ -d "$BUNDLE_DIR" ]; then
  echo "ERROR: Directory '$BUNDLE_DIR' already exists."
  exit 1
fi

echo "Creating agent bundle skeleton: $BUNDLE_NAME"

mkdir -p "$BUNDLE_DIR"/{src,tests,evals}

# manifest.json
cat > "$BUNDLE_DIR/manifest.json" <<EOF
{
  "name": "$BUNDLE_NAME",
  "version": "0.1.0",
  "description": "Agent bundle for $BUNDLE_NAME",
  "author": "$(git config user.name 2>/dev/null || echo 'developer')",
  "category": "general",
  "min_platform_version": "1.7.0",
  "agent_definition": {
    "name": "$BUNDLE_NAME",
    "instructions": "You are a helpful agent.",
    "model_id": "gpt-4o",
    "allowed_tools": []
  },
  "tool_requirements": [],
  "memory_policy": {
    "type": "short_term",
    "retention_days": 7
  },
  "eval_suite": {
    "name": "$BUNDLE_NAME evals",
    "cases": []
  },
  "checksums": {}
}
EOF

# instructions.md
cat > "$BUNDLE_DIR/src/instructions.md" <<'EOF'
# Agent Instructions

You are a helpful AI assistant. Your job is to assist users with their tasks.

## Guidelines
- Be concise and accurate
- Ask clarifying questions when needed
- Always cite sources when possible
EOF

# placeholder test
cat > "$BUNDLE_DIR/tests/test_basic.py" <<'EOF'
"""Basic agent tests."""
import json
import os

def test_manifest_exists():
    assert os.path.exists("manifest.json"), "manifest.json not found"

def test_manifest_valid():
    with open("manifest.json") as f:
        data = json.load(f)
    assert "name" in data
    assert "version" in data
    assert "agent_definition" in data
EOF

# placeholder eval
cat > "$BUNDLE_DIR/evals/eval_cases.json" <<'EOF'
{
  "name": "Basic functionality",
  "cases": [
    {
      "input": "Hello, who are you?",
      "expected_contains": "agent"
    }
  ]
}
EOF

# .gitignore
cat > "$BUNDLE_DIR/.gitignore" <<'EOF'
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
EOF

# README.md
cat > "$BUNDLE_DIR/README.md" <<EOF
# $BUNDLE_NAME

Agent bundle created with \`agentctl bundle init\`.

## Structure
- \`manifest.json\` — Bundle manifest
- \`src/\` — Agent source code
- \`tests/\` — Test suite
- \`evals/\` — Evaluation cases

## Next Steps
1. Edit \`manifest.json\` with your agent configuration
2. Write instructions in \`src/instructions.md\`
3. Run \`./agent-bundle-validate.sh\` to validate
4. Run \`./agent-bundle-test.sh\` to test
5. Run \`./agent-bundle-sign.sh\` to sign
6. Run \`./agent-bundle-publish.sh\` to publish
EOF

echo ""
echo "Bundle skeleton created: $BUNDLE_DIR"
echo ""
echo "Contents:"
find "$BUNDLE_DIR" -type f | sort | sed 's/^/  /'
echo ""
echo "Next: Edit manifest.json, then run agent-bundle-validate.sh"
