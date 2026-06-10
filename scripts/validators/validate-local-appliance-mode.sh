#!/usr/bin/env bash
# scripts/validators/validate-local-appliance-mode.sh
# Validates LOCAL_APPLIANCE_MODE configuration and behavior.

set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost:18080"}
ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" .env.local 2>/dev/null | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "default-admin-token")

log() {
  echo "[INFO] $1"
}

error() {
  echo "[ERROR] $1"
  exit 1
}

warn() {
  echo "[WARN] $1"
}

log "Validating LOCAL_APPLIANCE_MODE..."

# 1. Check if variable is recognized in .env.local
if ! grep -q "^LOCAL_APPLIANCE_MODE=true" .env.local; then
  error "LOCAL_APPLIANCE_MODE=true not found in .env.local"
fi

# 2. Check /status endpoint
log "Checking /status endpoint..."
STATUS_JSON=$(curl -s "${BASE_URL}/status")
if [[ $(echo "$STATUS_JSON" | jq -r '.appliance_mode') != "true" ]]; then
  error "/status does not show appliance_mode=true"
fi
log "/status shows appliance_mode=true"

# 3. Check /admin/health/deep endpoint
log "Checking /admin/health/deep endpoint..."
DEEP_JSON=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/health/deep")
if [[ $(echo "$DEEP_JSON" | jq -r '.api.appliance_mode') != "true" ]]; then
  error "/admin/health/deep does not show api.appliance_mode=true"
fi
log "/admin/health/deep shows appliance_mode=true"

# 4. Check billing mode
BILLING_MODE=$(echo "$DEEP_JSON" | jq -r '.billing.mode')
if [[ "$BILLING_MODE" != "manual" ]]; then
  error "Billing mode is '$BILLING_MODE', expected 'manual' in appliance mode"
fi
log "Billing mode is manual"

# 5. Check security warnings (e.g., default token)
if [[ "$ADMIN_TOKEN" == "default-admin-token" ]]; then
  if ! echo "$DEEP_JSON" | jq -r '.warnings[]' | grep -q "Insecure default ADMIN_TOKEN"; then
    error "Insecure default ADMIN_TOKEN used but no warning found in /admin/health/deep"
  fi
  warn "Default ADMIN_TOKEN warning confirmed"
fi

# 6. Check release bundle exclusions
log "Checking release bundle exclusions..."
if ! grep -q "\"models\"" scripts/release/create-release-bundle.sh; then
  error "models/ not excluded in scripts/release/create-release-bundle.sh"
fi
if ! grep -q "\"data/rag_uploads\"" scripts/release/create-release-bundle.sh; then
  error "data/rag_uploads/ not excluded in scripts/release/create-release-bundle.sh"
fi
log "Release bundle exclusions confirmed"

# 7. Check release guards
log "Checking release guards..."
if ! grep -q "LOCAL_APPLIANCE_MODE" scripts/release/release-local-production.sh; then
  error "LOCAL_APPLIANCE_MODE guards missing in scripts/release/release-local-production.sh"
fi
log "Release guards confirmed"

log "LOCAL_APPLIANCE_MODE validation passed!"
exit 0
