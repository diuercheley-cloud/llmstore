#!/usr/bin/env bash
# Validate the release history document.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RELEASE_HISTORY="${PROJECT_ROOT}/docs/RELEASE_HISTORY.md"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf "  [PASS] %s\n" "$1"; }
fail() { FAIL=$((FAIL + 1)); printf "  [FAIL] %s\n" "$1"; }
section() { printf "\n=== %s ===\n" "$1"; }

section "1. File exists"
if [[ -f "$RELEASE_HISTORY" ]]; then
  pass "docs/RELEASE_HISTORY.md exists"
else
  fail "docs/RELEASE_HISTORY.md is missing"
fi

section "2. Required tags are present"
REQUIRED_TAGS=("v1.5.3-local-ops" "v1.5.4-security-cleanup" "v1.5.5-security-artifacts-clean"
  "v1.5.6-runtime-hardening" "v1.6.0-openai-compat" "v1.6.1-product-hardening"
  "v1.6.2-installer-polish" "v1.6.3-readiness-cleanup" "v1.6.4-customer-demo-pack" "v1.6.5-sales-ops")
for tag in "${REQUIRED_TAGS[@]}"; do
  if grep -q "$tag" "$RELEASE_HISTORY" 2>/dev/null; then
    pass "Tag $tag found in RELEASE_HISTORY"
  else
    fail "Tag $tag missing from RELEASE_HISTORY"
  fi
done

section "3. Stable branches documented"
for branch in stable/v1.5.3-local-ops stable/v1.5.4-security-cleanup stable/v1.5.5-security-artifacts-clean \
  stable/v1.5.6-runtime-hardening stable/v1.6.0-openai-compat stable/v1.6.1-product-hardening \
  stable/v1.6.2-installer-polish stable/v1.6.3-readiness-cleanup stable/v1.6.4-customer-demo-pack \
  stable/v1.6.5-sales-ops; do
  if grep -q "$branch" "$RELEASE_HISTORY" 2>/dev/null; then
    pass "Branch $branch documented"
  else
    fail "Branch $branch not documented"
  fi
done

section "4. No secrets in document"
SECRET_PATTERNS=("sk-[a-zA-Z0-9]" "ghp_" "-----BEGIN" "ADMIN_TOKEN=" "JWT_SECRET=")
for pat in "${SECRET_PATTERNS[@]}"; do
  if grep -qE "$pat" "$RELEASE_HISTORY" 2>/dev/null; then
    fail "Secret pattern '$pat' found in RELEASE_HISTORY"
  else
    pass "No secret pattern '$pat' in RELEASE_HISTORY"
  fi
done

section "5. Required sections exist"
REQUIRED_SECTIONS=(
  "Visao Geral"
  "Linha do Tempo"
  "Releases Recomendadas"
  "Releases Antigas"
  "Como Restaurar"
  "Como Criar uma Nova Release"
  "Politica de Branches"
)
for section_title in "${REQUIRED_SECTIONS[@]}"; do
  if grep -qi "$section_title" "$RELEASE_HISTORY" 2>/dev/null; then
    pass "Section '$section_title' found"
  else
    fail "Section '$section_title' missing"
  fi
done

section "6. Paths are relative"
for path in releases/ docs/ scripts/; do
  if grep -q "$path" "$RELEASE_HISTORY" 2>/dev/null; then
    pass "Relative path $path used"
    break
  fi
done

section "Summary"
echo ""
echo "  $PASS PASS, $FAIL FAIL"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
