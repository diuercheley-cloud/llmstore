#!/usr/bin/env bash
set -euo pipefail

# scripts/validate-release-artifacts-security.sh
# Validates that release artifacts do not contain sensitive information.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
RELEASES_DIR="${ROOT_DIR}/releases"

echo "Checking releases security..."

if [[ ! -d "${RELEASES_DIR}" ]]; then
    echo "No releases directory found. Skipping."
    exit 0
fi

# 1. Check for .tar.gz files that might be staged or tracked
# (They should be ignored by .gitignore, but we double check)
TRACKED_TARBALLS=$(git -C "${ROOT_DIR}" ls-files "${RELEASES_DIR}/**/*.tar.gz" || echo "")
if [[ -n "${TRACKED_TARBALLS}" ]]; then
    echo "FAIL: Found .tar.gz files tracked by Git in releases/:"
    echo "${TRACKED_TARBALLS}"
    exit 1
fi

# 2. Check for logs/ directories in releases/
LOGS_DIRS=$(find "${RELEASES_DIR}" -type d -name "logs")
if [[ -n "${LOGS_DIRS}" ]]; then
    echo "FAIL: Found logs/ directories in releases/:"
    echo "${LOGS_DIRS}"
    exit 1
fi

# 3. Check for secrets in manifests and summaries
# Patterns to look for:
# - sk-... (OpenAI/other API keys)
# - Bearer ...
# - ADMIN_TOKEN=... (if not redacted)
SECRETS_FOUND=$(grep -rIE "sk-[a-zA-Z0-9]{20,}|Bearer [a-zA-Z0-9]{20,}|ADMIN_TOKEN=[^#_][^r][^e][^d][^a][^c][^t]" "${RELEASES_DIR}" --exclude="*.sha256" || echo "")

# Note: The ADMIN_TOKEN regex above tries to avoid matching "__redacted__" 
# but a simpler way is to grep and then filter out redacted.
SECRETS_CLEANED=$(echo "${SECRETS_FOUND}" | grep -v "__redacted__" | grep -v "change-this-admin-token" || echo "")

if [[ -n "${SECRETS_CLEANED}" ]]; then
    echo "FAIL: Found potential secrets in releases/:"
    echo "${SECRETS_CLEANED}"
    exit 1
fi

# 4. Verify that .gitignore contains the rule for tar.gz in releases
if ! grep -q "releases/\*\*/\*.tar.gz" "${ROOT_DIR}/.gitignore"; then
    echo "FAIL: .gitignore does not contain 'releases/**/*.tar.gz'"
    exit 1
fi

echo "SUCCESS: Releases security validation passed."
exit 0
