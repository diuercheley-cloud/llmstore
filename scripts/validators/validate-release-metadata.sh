#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

VERSION=""
RELEASE_DIR=""
OLD_VERSION="v1.4.4-local-demo"

usage() {
    echo "Usage: $0 --version <vX.Y.Z> --release-dir <path>"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --release-dir) RELEASE_DIR="$2"; shift 2 ;;
        *) usage ;;
    esac
done

if [[ -z "${VERSION}" || -z "${RELEASE_DIR}" ]]; then
    usage
fi

if [[ "${RELEASE_DIR}" != /* ]]; then
    RELEASE_DIR="${ROOT_DIR}/${RELEASE_DIR}"
fi

MANIFEST_JSON="${RELEASE_DIR}/release-manifest.json"
SUMMARY_JSON="${RELEASE_DIR}/summary.json"
SUMMARY_MD="${RELEASE_DIR}/summary.md"
CURRENT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo "unknown")"

fail() {
    echo "[release-metadata][error] $*" >&2
    exit 1
}

[[ -f "${MANIFEST_JSON}" ]] || fail "missing release-manifest.json"
[[ -f "${SUMMARY_JSON}" ]] || fail "missing summary.json"
[[ -f "${SUMMARY_MD}" ]] || fail "missing summary.md"

python3 - "${VERSION}" "${CURRENT_COMMIT}" "${MANIFEST_JSON}" "${SUMMARY_JSON}" <<'PY'
import json
import sys

expected_version, current_commit, manifest_path, summary_path = sys.argv[1:5]

def fail(message):
    print(f"[release-metadata][error] {message}", file=sys.stderr)
    sys.exit(1)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        fail(f"cannot read {path}: {exc}")

manifest = load_json(manifest_path)
summary = load_json(summary_path)

def normalize_commit(value):
    if value is None:
        return "unknown"
    value = str(value).strip()
    if not value or value in {"unknown", "not-a-git-repo"}:
        return "unknown"
    return value

if manifest.get("version") != expected_version:
    fail(f"release-manifest.json version mismatch: {manifest.get('version')} != {expected_version}")
if summary.get("version") != expected_version:
    fail(f"summary.json version mismatch: {summary.get('version')} != {expected_version}")

current_commit = normalize_commit(current_commit)
manifest_commit = normalize_commit(manifest.get("git_commit"))
summary_commit = normalize_commit(summary.get("git_commit"))

if "validated_commit" not in manifest and manifest_commit != current_commit:
    fail(f"release-manifest.json git_commit mismatch: {manifest_commit} != {current_commit}")
if "validated_commit" not in summary and summary_commit != current_commit:
    fail(f"summary.json git_commit mismatch: {summary_commit} != {current_commit}")

for field in ("psp_integration", "pix_real_billing", "models_included", "rag_uploads_included"):
    if manifest.get(field) is not False:
        fail(f"release-manifest.json {field} must be false")
if manifest.get("localhost_mode") is not True:
    fail("release-manifest.json localhost_mode must be true")

if manifest.get("validation_result") != "success":
    fail(f"release-manifest.json validation_result must be success, got {manifest.get('validation_result')}")
PY

grep -Fq "**Version:** ${VERSION}" "${SUMMARY_MD}" || fail "summary.md version marker mismatch"

if grep -R -F "${OLD_VERSION}" "${RELEASE_DIR}" >/dev/null 2>&1; then
    fail "old version ${OLD_VERSION} found in ${RELEASE_DIR}"
fi

if find "${RELEASE_DIR}" -type f \( \
    -name '*.gguf' -o \
    -path '*/models/*' -o \
    -path '*/data/rag_uploads/*' -o \
    -name '.env' -o \
    -path '*/.local/*' -o \
    -path '*/backups/*' -o \
    -path '*/exports/*' \
  \) | grep -q .; then
    fail "release directory contains excluded files or directories"
fi

if grep -R -E \
    'sk-[a-zA-Z0-9]{20,}|ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}|JWT_SECRET=[a-zA-Z0-9._-]{12,}|ghp_[a-zA-Z0-9]{36}|Bearer [a-zA-Z0-9._-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost|127\.0\.0\.1)' \
    "${RELEASE_DIR}" >/dev/null 2>&1; then
    fail "potential secret found in ${RELEASE_DIR}"
fi

echo "[release-metadata] OK ${VERSION}"
