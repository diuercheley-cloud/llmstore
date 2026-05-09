#!/usr/bin/env bash
set -e

echo "Validating .gitignore security patterns..."

GITIGNORE=".gitignore"
if [ ! -f "$GITIGNORE" ]; then
    echo "Error: .gitignore not found"
    exit 1
fi

check_pattern() {
    local pattern=$1
    if ! grep -qF "$pattern" "$GITIGNORE"; then
        echo "Error: Missing required pattern '$pattern' in $GITIGNORE"
        exit 1
    fi
}

# Required patterns
check_pattern ".env"
check_pattern ".env.*"
check_pattern "!.env.example"
check_pattern "!.env.local.example"
check_pattern ".local/"
check_pattern "artifacts/"
check_pattern "exports/"
check_pattern "backups/"
check_pattern "data/rag_uploads/"
check_pattern "models/"
check_pattern "*.gguf"
check_pattern "*.safetensors"
check_pattern "*.bin"
check_pattern "releases/**/*.tar.gz"
check_pattern "releases/**/logs/"
check_pattern "releases/**/raw-results*"
check_pattern "__pycache__/"
check_pattern ".pytest_cache/"
check_pattern ".mypy_cache/"
check_pattern ".ruff_cache/"
check_pattern "node_modules/"

# Required exceptions
check_pattern "!releases/**/release-manifest.json"
check_pattern "!releases/**/summary.json"
check_pattern "!releases/**/summary.md"
check_pattern "!releases/**/bundle-manifest.json"
check_pattern "!releases/**/bundle-checksums.sha256"

# Key exceptions
check_pattern "*.pem"
check_pattern "*.key"
check_pattern "!tests/fixtures/fake_*.pem"
check_pattern "!tests/fixtures/fake_*.key"

echo ".gitignore security validation passed!"