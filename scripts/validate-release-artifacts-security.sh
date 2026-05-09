#!/usr/bin/env bash
set -euo pipefail

# scripts/validate-release-artifacts-security.sh
# Validates that release artifacts do not contain sensitive information.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
RELEASES_DIR="${ROOT_DIR}/releases"

TARGET_DIR="${RELEASES_DIR}"
SPECIFIC_RELEASE=""

usage() {
    echo "Usage: $0 [--release-dir <path>]"
    echo "  --release-dir: Path to a specific release directory to validate"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --release-dir) TARGET_DIR="$2"; SPECIFIC_RELEASE="$2"; shift 2 ;;
        *) usage ;;
    esac
done

echo "Checking releases security in: ${TARGET_DIR}"

if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "Error: Target directory ${TARGET_DIR} not found."
    exit 1
fi

# 1. Check for .tar.gz files that might be staged or tracked
# They should NOT be in the repository.
echo "Checking for versioned tarballs..."
TRACKED_TARBALLS=$(git -C "${ROOT_DIR}" ls-files "${TARGET_DIR}/**/*.tar.gz" "${TARGET_DIR}/*.tar.gz" 2>/dev/null || echo "")
if [[ -n "${TRACKED_TARBALLS}" ]]; then
    echo "FAIL: Found .tar.gz files tracked by Git in releases/:"
    echo "${TRACKED_TARBALLS}"
    exit 1
fi

# 2. Check for logs/ directories in releases/
echo "Checking for logs directories..."
LOGS_DIRS=$(find "${TARGET_DIR}" -type d -name "logs")
if [[ -n "${LOGS_DIRS}" ]]; then
    echo "FAIL: Found logs/ directories in releases/:"
    echo "${LOGS_DIRS}"
    exit 1
fi

# 3. Check for secrets in manifests and summaries
echo "Scanning for secrets..."
# Patterns to look for (extending what's in check-secrets.sh)
SECRET_REGEXES=(
    "sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"
    "ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"
    "JWT_SECRET=[a-zA-Z0-9._-]{12,}"
    "ghp_[a-zA-Z0-9]{36}"
    "Bearer [a-zA-Z0-9._-]{20,}"
    "Authorization: Bearer [a-zA-Z0-9._-]{20,}"
    "\"Authorization\": \"Bearer [a-zA-Z0-9._-]{20,}\""
    "\"api_key\": \"[a-zA-Z0-9._-]{20,}\""
    "\"api-key\": \"[a-zA-Z0-9._-]{20,}\""
    "\"access_token\": \"[a-zA-Z0-9._-]{20,}\""
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
)

SAFE_PATTERNS=(
    "__redacted__"
    "change-this-admin-token"
    "admin-token-example"
    "sk-local-example"
    "your-api-key"
    "placeholder"
)

# Build grep regex
COMBINED_REGEX=$(IFS='|'; echo "${SECRET_REGEXES[*]}")
SAFE_REGEX=$(IFS='|'; echo "${SAFE_PATTERNS[*]}")

# Find all files in target dir excluding .sha256 and .tar.gz (which shouldn't be there anyway)
FILES_TO_SCAN=$(find "${TARGET_DIR}" -type f ! -name "*.sha256" ! -name "*.tar.gz" ! -name "*.zip")

if [[ -n "${FILES_TO_SCAN}" ]]; then
    SECRETS_FOUND=$(grep -Eon "${COMBINED_REGEX}" ${FILES_TO_SCAN} | grep -vE "${SAFE_REGEX}" || true)

    if [[ -n "${SECRETS_FOUND}" ]]; then
        echo "FAIL: Found potential secrets in release artifacts:"
        echo "${SECRETS_FOUND}"
        exit 1
    fi
fi

# 4. Validate bundle-checksums.sha256 if it exists
CHECKSUM_FILES=$(find "${TARGET_DIR}" -name "bundle-checksums.sha256")
for cf in ${CHECKSUM_FILES}; do
    echo "Validating checksum file: ${cf}"
    # Each line should be: <64-char-hex>  <filename>
    # Filenames allowed: llm-inference-stack-*.tar.gz
    INVALID_LINES=$(grep -vE "^[a-f0-9]{64}  llm-inference-stack-.*\.tar\.gz$" "${cf}" || true)
    if [[ -n "${INVALID_LINES}" ]]; then
        echo "FAIL: Invalid lines or unallowed filenames in ${cf}:"
        echo "${INVALID_LINES}"
        exit 1
    fi
done

# 5. Check for sensitive filenames/extensions that shouldn't be in releases
# e.g. .env, .pem, .key
echo "Checking for sensitive file types..."
SENSITIVE_FILES=$(find "${TARGET_DIR}" -name ".env" -o -name "*.pem" -o -name "*.key" -o -name "*.crt" -o -name "*.db" -o -name "*.sqlite")
if [[ -n "${SENSITIVE_FILES}" ]]; then
    echo "FAIL: Found sensitive files in releases/:"
    echo "${SENSITIVE_FILES}"
    exit 1
fi

# 6. Verify that .gitignore contains the rule for tar.gz in releases
# (Only if we are checking the whole releases dir or from root)
if [[ -f "${ROOT_DIR}/.gitignore" ]]; then
    if ! grep -q "releases/\*\*/\*.tar.gz" "${ROOT_DIR}/.gitignore"; then
        echo "FAIL: .gitignore does not contain 'releases/**/*.tar.gz'"
        exit 1
    fi
fi

echo "SUCCESS: Release artifacts security validation passed for ${TARGET_DIR}."
exit 0
