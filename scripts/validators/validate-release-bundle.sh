#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TEST_VERSION="v-test-bundle"
OUTPUT_DIR="releases"
TEST_BUNDLE_DIR="$OUTPUT_DIR/$TEST_VERSION"
EXTRACT_DIR="tmp_validate_bundle"

echo -e "${YELLOW}Starting release bundle validation...${NC}"

# Cleanup
rm -rf "$TEST_BUNDLE_DIR"
rm -rf "$EXTRACT_DIR"

# 1. Create bundle
echo "Creating test bundle..."
./scripts/release/create-release-bundle.sh --version "$TEST_VERSION" --include-docs --include-examples --include-demo

# 2. Extract bundle
echo "Extracting bundle..."
mkdir -p "$EXTRACT_DIR"
ARCHIVE_PATH="$TEST_BUNDLE_DIR/llm-inference-stack-$TEST_VERSION.tar.gz"
tar -xzf "$ARCHIVE_PATH" -C "$EXTRACT_DIR"

BUNDLE_ROOT="$EXTRACT_DIR/llm-inference-stack-$TEST_VERSION"

# 3. Fail if forbidden files are found
echo "Checking for forbidden files..."
FORBIDDEN=(
    ".env"
    ".env.local"
    ".local"
    "models"
    "data/rag_uploads"
    "backups"
    "exports"
    ".git"
    ".venv"
    "node_modules"
)

EXIT_CODE=0

for f in "${FORBIDDEN[@]}"; do
    if [ -e "$BUNDLE_ROOT/$f" ]; then
        echo -e "${RED}Error: Forbidden file/directory found in bundle: $f${NC}"
        EXIT_CODE=1
    fi
done

# Check for .gguf files
GGUF_COUNT=$(find "$BUNDLE_ROOT" -name "*.gguf" | wc -l)
if [ "$GGUF_COUNT" -gt 0 ]; then
    echo -e "${RED}Error: GGUF files found in bundle.${NC}"
    EXIT_CODE=1
fi

# 4. Validate manifest
echo "Validating bundle-manifest.json..."
MANIFEST_PATH="$TEST_BUNDLE_DIR/bundle-manifest.json"
if [ ! -f "$MANIFEST_PATH" ]; then
    echo -e "${RED}Error: bundle-manifest.json not found.${NC}"
    EXIT_CODE=1
else
    # Basic check if it's valid JSON and contains key fields
    grep -q "\"version\": \"$TEST_VERSION\"" "$MANIFEST_PATH" || (echo -e "${RED}Manifest version mismatch${NC}"; EXIT_CODE=1)
    grep -q "\"secrets_scan_passed\": true" "$MANIFEST_PATH" || (echo -e "${RED}Manifest secrets check failed${NC}"; EXIT_CODE=1)
fi

# 5. Validate SHA256
echo "Validating checksum..."
CHECKSUM_PATH="$TEST_BUNDLE_DIR/bundle-checksums.sha256"
if [ ! -f "$CHECKSUM_PATH" ]; then
    echo -e "${RED}Error: bundle-checksums.sha256 not found.${NC}"
    EXIT_CODE=1
else
    cd "$TEST_BUNDLE_DIR"
    sha256sum -c "bundle-checksums.sha256" || (echo -e "${RED}Checksum validation failed${NC}"; EXIT_CODE=1)
    cd - > /dev/null
fi

# 6. Run check-secrets on extracted content
echo "Running secrets scan on extracted content..."
if [ -f "./scripts/validators/check-secrets.sh" ]; then
    ./scripts/validators/check-secrets.sh --path "$BUNDLE_ROOT" || (echo -e "${RED}Secrets scan failed on extracted content${NC}"; EXIT_CODE=1)
else
    echo -e "${YELLOW}Warning: scripts/validators/check-secrets.sh not found, skipping final scan.${NC}"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Bundle validation PASSED!${NC}"
else
    echo -e "${RED}Bundle validation FAILED!${NC}"
fi

# Cleanup
rm -rf "$TEST_BUNDLE_DIR"
rm -rf "$EXTRACT_DIR"

exit $EXIT_CODE
