#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VERSION=""
OUTPUT_DIR="releases"
INCLUDE_DOCS=false
INCLUDE_EXAMPLES=false
INCLUDE_DEMO=false
DRY_RUN=false

show_help() {
    echo "Usage: $0 --version <vX.Y.Z> [options]"
    echo ""
    echo "Options:"
    echo "  --version vX.Y.Z      Version of the release bundle"
    echo "  --output-dir <dir>    Directory to save the bundle (default: releases/)"
    echo "  --include-docs        Include docs/ directory"
    echo "  --include-examples    Include examples/ directory"
    echo "  --include-demo        Include demo/ directory"
    echo "  --dry-run             Do not create the final archive"
    echo "  --help                Show this help message"
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) VERSION="$2"; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift ;;
        --include-docs) INCLUDE_DOCS=true ;;
        --include-examples) INCLUDE_EXAMPLES=true ;;
        --include-demo) INCLUDE_DEMO=true ;;
        --dry-run) DRY_RUN=true ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

if [[ -z "$VERSION" ]]; then
    echo -e "${RED}Error: --version is required.${NC}"
    show_help
    exit 1
fi

STAGING_DIR="tmp_release_bundle_$VERSION"
BUNDLE_NAME="llm-inference-stack-$VERSION"
ARCHIVE_NAME="$BUNDLE_NAME.tar.gz"
FINAL_DEST="$OUTPUT_DIR/$VERSION"

echo -e "${YELLOW}Starting release bundle creation for $VERSION...${NC}"

# Cleanup previous attempts
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/$BUNDLE_NAME"

# Mandatory exclusions for copy operations
EXCLUSIONS=(
    ".git"
    ".venv"
    "node_modules"
    "__pycache__"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    ".env"
    ".env.local"
    ".local"
    "models"
    "data/rag_uploads"
    "backups"
    "exports"
    "artifacts"
    "*.gguf"
    "*.pem"
    "*.key"
    "*.tar.gz"
)

RSYNC_EXCLUDES=()
TAR_EXCLUDES=()
for exc in "${EXCLUSIONS[@]}"; do
    RSYNC_EXCLUDES+=(--exclude="$exc")
    TAR_EXCLUDES+=(--exclude="$exc")
done

# Paths to include
PATHS_TO_INCLUDE=(
    "control_plane"
    "data_plane_mock"
    "docker"
    "scripts"
    "Makefile"
    "README.md"
    "CHANGELOG.md"
    "VERSION"
    "docker-compose.yml"
    "docker-compose.prod.yml"
    "test-compose.yml"
    "test-override.yml"
    ".env.example"
)

if [ "$INCLUDE_DOCS" = true ]; then PATHS_TO_INCLUDE+=("docs"); fi
if [ "$INCLUDE_EXAMPLES" = true ]; then PATHS_TO_INCLUDE+=("examples"); fi
if [ "$INCLUDE_DEMO" = true ]; then PATHS_TO_INCLUDE+=("demo"); fi

# Also include .env.local.example if exists
if [ -f ".env.local.example" ]; then PATHS_TO_INCLUDE+=(".env.local.example"); fi

# Also include config/*.example.* if exists
if compgen -G "config/*.example.*" > /dev/null; then
    mkdir -p "$STAGING_DIR/$BUNDLE_NAME/config"
    cp config/*.example.* "$STAGING_DIR/$BUNDLE_NAME/config/"
fi

# Copy a directory tree with exclusions, even when rsync is unavailable.
copy_tree() {
    local src="$1"
    local dest="$2"

    mkdir -p "$dest"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a "${RSYNC_EXCLUDES[@]}" "${src}/" "${dest}/"
        return
    fi

    tar -cf - -C "$src" "${TAR_EXCLUDES[@]}" . | tar -xf - -C "$dest"
}

# Copy project files into the staging tree
echo "Copying files to staging..."
for p in "${PATHS_TO_INCLUDE[@]}"; do
    if [ -e "$p" ]; then
        if [ -d "$p" ]; then
            copy_tree "$p" "$STAGING_DIR/$BUNDLE_NAME/$p"
        else
            mkdir -p "$(dirname "$STAGING_DIR/$BUNDLE_NAME/$p")"
            cp "$p" "$STAGING_DIR/$BUNDLE_NAME/$p"
        fi
    else
        echo -e "${YELLOW}Warning: Path $p not found, skipping.${NC}"
    fi
done

# Run check-secrets on staging
echo "Running secrets scan on staging..."
SECRETS_PASSED=true
if [ -f "./scripts/validators/check-secrets.sh" ]; then
    ./scripts/validators/check-secrets.sh --path "$STAGING_DIR/$BUNDLE_NAME" || SECRETS_PASSED=false
else
    echo -e "${YELLOW}Warning: scripts/validators/check-secrets.sh not found, skipping scan.${NC}"
fi

if [ "$SECRETS_PASSED" = false ]; then
    echo -e "${RED}Error: Secrets detected in the staging directory! Aborting.${NC}"
    rm -rf "$STAGING_DIR"
    exit 1
fi

# Gather metadata for manifest
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
FILES_COUNT=$(find "$STAGING_DIR/$BUNDLE_NAME" -type f | wc -l)

# Create the archive
if [ "$DRY_RUN" = false ]; then
    echo "Creating archive..."
    mkdir -p "$FINAL_DEST"
    tar -czf "$FINAL_DEST/$ARCHIVE_NAME" -C "$STAGING_DIR" "$BUNDLE_NAME"
    ARCHIVE_SHA256=$(sha256sum "$FINAL_DEST/$ARCHIVE_NAME" | cut -d' ' -f1)
    echo "$ARCHIVE_SHA256  $ARCHIVE_NAME" > "$FINAL_DEST/bundle-checksums.sha256"
else
    echo -e "${YELLOW}Dry run enabled, skipping archive creation.${NC}"
    ARCHIVE_SHA256="dry-run"
fi

# Generate bundle-manifest.json
echo "Generating manifest..."
mkdir -p "$FINAL_DEST"
cat <<EOF > "$FINAL_DEST/bundle-manifest.json"
{
  "version": "$VERSION",
  "git_branch": "$GIT_BRANCH",
  "git_commit": "$GIT_COMMIT",
  "generated_at": "$GENERATED_AT",
  "included_paths": [$(printf '"%s",' "${PATHS_TO_INCLUDE[@]}" | sed 's/,$//')],
  "excluded_paths": [$(printf '"%s",' "${EXCLUSIONS[@]}" | sed 's/,$//')],
  "files_count": $FILES_COUNT,
  "archive_name": "$ARCHIVE_NAME",
  "archive_sha256": "$ARCHIVE_SHA256",
  "secrets_scan_passed": $SECRETS_PASSED,
  "models_included": false,
  "rag_uploads_included": false,
  "env_included": false,
  "local_data_included": false
}
EOF

echo "Validating release bundle artifacts security..."
if ! "./scripts/validators/validate-release-artifacts-security.sh" --release-dir "$FINAL_DEST"; then
    echo -e "${RED}Error: Security validation failed for $FINAL_DEST!${NC}"
    exit 1
fi

if [ "$DRY_RUN" = false ]; then
    echo -e "${GREEN}Release bundle created successfully at $FINAL_DEST/$ARCHIVE_NAME${NC}"
    echo "Size: $(du -sh "$FINAL_DEST/$ARCHIVE_NAME" | cut -f1)"
    echo "SHA256: $ARCHIVE_SHA256"
fi

rm -rf "$STAGING_DIR"
