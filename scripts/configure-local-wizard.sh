#!/usr/bin/env bash
# LLM Inference Stack - Local Appliance Configuration Wizard
# Guided setup for local appliance mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")

# Load operator errors library
if [[ -f "${ROOT_DIR}/lib/operator-errors.sh" ]]; then
  source "${ROOT_DIR}/scripts/lib/operator-errors.sh"
fi

if ! declare -F operator_success >/dev/null; then
  operator_success() {
    echo "[SUCCESS] $1"
  }
fi

if ! declare -F add_next_step >/dev/null; then
  add_next_step() {
    :
  }
fi

if ! declare -F print_next_steps >/dev/null; then
  print_next_steps() {
    :
  }
fi

ENV_FILE="${ROOT_DIR}/.env.local"
BACKUP_DIR="${ROOT_DIR}/.local/backups/env"
SUMMARY_DIR="${ROOT_DIR}/.local/install"

# Default values
INTERACTIVE=true
YES=false
DRY_RUN=false
GPU=false
CPU_ONLY=false
ENABLE_DEMO=false
DISABLE_DEMO=false
BASE_URL="http://localhost:18080"
HOST_PORT="18080"
ADMIN_EMAIL=""
MODELS_PATH="${ROOT_DIR}/models"

show_help() {
  echo "LLM Inference Stack - Local Appliance Configuration Wizard v${VERSION}"
  echo ""
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --interactive       Run in interactive mode (default)"
  echo "  --non-interactive   Run in non-interactive mode"
  echo "  --yes               Skip confirmations in non-interactive mode"
  echo "  --dry-run           Show what would be done without doing it"
  echo "  --base-url URL      Set public base URL (default: http://localhost:18080)"
  echo "  --host-port PORT    Set host port (default: 18080)"
  echo "  --gpu               Enable GPU mode"
  echo "  --cpu-only          Enable CPU-only mode"
  echo "  --enable-demo       Enable local demo mode"
  echo "  --disable-demo      Disable local demo mode"
  echo "  --admin-email EMAIL Set admin email"
  echo "  --help              Show this help"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --interactive) INTERACTIVE=true; shift ;;
    --non-interactive) INTERACTIVE=false; shift ;;
    --yes) YES=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --host-port) HOST_PORT="$2"; shift 2 ;;
    --gpu) GPU=true; shift ;;
    --cpu-only) CPU_ONLY=true; shift ;;
    --enable-demo) ENABLE_DEMO=true; shift ;;
    --disable-demo) DISABLE_DEMO=true; shift ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

log() {
  echo "[INFO] $1"
}

warn() {
  if declare -F operator_warning >/dev/null; then
    operator_warning "VALIDATION_FAILED" "$1" "Verifique as configurações informadas."
  else
    echo "[WARN] $1"
  fi
}

error() {
  if declare -F operator_error >/dev/null; then
    operator_error "VALIDATION_FAILED" "$1" "Verifique as configurações informadas e tente novamente."
  else
    echo "[ERROR] $1"
  fi
  exit 1
}

mask_token() {
  local token=$1
  if [[ ${#token} -le 8 ]]; then
    echo "********"
  else
    echo "${token:0:4}...${token: -4}"
  fi
}

ask_question() {
  local prompt=$1
  local default=$2
  local result_var=$3
  local input

  if [ "$INTERACTIVE" = true ]; then
    read -p "$prompt [$default]: " input
    if [[ -z "$input" ]]; then
      eval "$result_var=\"$default\""
    else
      eval "$result_var=\"$input\""
    fi
  else
    eval "$result_var=\"$default\""
  fi
}

ask_confirm() {
  local prompt=$1
  local default=$2 # y or n
  local input

  if [ "$INTERACTIVE" = true ]; then
    read -p "$prompt ($default/other): " input
    input=${input:-$default}
    if [[ "$input" =~ ^[Yy]$ ]]; then
      return 0
    else
      return 1
    fi
  else
    if [ "$YES" = true ]; then
      return 0
    else
      return 1
    fi
  fi
}

# Banner
echo "===================================================="
echo "    Local Appliance Configuration Wizard"
echo "    Version: ${VERSION}"
echo "===================================================="
echo ""

# 1. Gather Information
if [ "$INTERACTIVE" = true ]; then
  ask_question "Desired Base URL" "$BASE_URL" BASE_URL
  ask_question "Host Port" "$HOST_PORT" HOST_PORT
  
  if ask_confirm "Enable GPU mode?" "n"; then
    GPU=true
    CPU_ONLY=false
  else
    GPU=false
    CPU_ONLY=true
  fi

  if ask_confirm "Enable local demo mode?" "n"; then
    ENABLE_DEMO=true
    DISABLE_DEMO=false
  else
    ENABLE_DEMO=false
    DISABLE_DEMO=true
  fi

  ask_question "Admin email (optional)" "$ADMIN_EMAIL" ADMIN_EMAIL
  ask_question "Path for models" "$MODELS_PATH" MODELS_PATH
fi

# 2. Validation & Security
log "Validating configuration..."

# 3. Dry Run Check
if [ "$DRY_RUN" = true ]; then
  echo "--- DRY RUN SUMMARY ---"
  echo "BASE_URL: $BASE_URL"
  echo "HOST_PORT: $HOST_PORT"
  echo "GPU: $GPU"
  echo "DEMO_MODE: $ENABLE_DEMO"
  echo "ADMIN_EMAIL: ${ADMIN_EMAIL:-N/A}"
  echo "MODELS_PATH: $MODELS_PATH"
  echo "-----------------------"
  echo "No changes were made."
  exit 0
fi

# 4. Preparation
mkdir -p "$BACKUP_DIR"
mkdir -p "$SUMMARY_DIR"
mkdir -p "$ROOT_DIR/.local"
chmod 700 "$ROOT_DIR/.local"

# 5. Backup .env.local
if [ -f "$ENV_FILE" ] && [ "${WIZARD_SKIP_ENV_BACKUP:-false}" != "true" ]; then
  TIMESTAMP=$(date +%Y%m%dT%H%M%S)
  BACKUP_FILE="${BACKUP_DIR}/.env.local.${TIMESTAMP}.bak"
  cp "$ENV_FILE" "$BACKUP_FILE"
  chmod 600 "$BACKUP_FILE"
  log "Backup created: $BACKUP_FILE"
else
  if [ -f "${ROOT_DIR}/.env.example" ]; then
    cp "${ROOT_DIR}/.env.example" "$ENV_FILE"
  else
    touch "$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE"
  log "Created new $ENV_FILE"
fi

# 6. Update .env.local
update_env() {
  local key=$1
  local val=$2
  if grep -q "^$key=" "$ENV_FILE"; then
    # Escape special characters for sed
    local escaped_val=$(echo "$val" | sed 's/[&/\]/\\&/g')
    sed -i "s|^$key=.*|$key=$escaped_val|" "$ENV_FILE"
  else
    echo "$key=$val" >> "$ENV_FILE"
  fi
}

update_env "LOCAL_APPLIANCE_MODE" "true"
update_env "LOCALHOST_MODE" "true"
update_env "LOCAL_BILLING_MODE" "manual"
update_env "BASE_URL" "$BASE_URL"
update_env "PUBLIC_BASE_URL" "$BASE_URL"
update_env "APP_PUBLIC_URL" "$BASE_URL"
update_env "HOST_PORT" "$HOST_PORT"

# Set secure CORS defaults
CORS_ORIGINS="http://localhost:${HOST_PORT},http://127.0.0.1:${HOST_PORT}"
if [[ "$BASE_URL" != "http://localhost:${HOST_PORT}" && "$BASE_URL" != "http://127.0.0.1:${HOST_PORT}" ]]; then
  # Remove trailing slash for CORS origin
  CLEAN_BASE_URL=$(echo "$BASE_URL" | sed 's|/$||')
  CORS_ORIGINS="${CORS_ORIGINS},${CLEAN_BASE_URL}"
fi
update_env "CORS_ALLOW_ORIGINS" "$CORS_ORIGINS"

if [ "$GPU" = true ]; then
  update_env "LLAMA_N_GPU_LAYERS" "20" # Default for GPU
elif [ "$CPU_ONLY" = true ]; then
  update_env "LLAMA_N_GPU_LAYERS" "0"
fi

if [ "$ENABLE_DEMO" = true ]; then
  update_env "DEMO_MODE" "true"
elif [ "$DISABLE_DEMO" = true ]; then
  update_env "DEMO_MODE" "false"
fi

if [ -n "$ADMIN_EMAIL" ]; then
  update_env "ADMIN_EMAIL" "$ADMIN_EMAIL"
  update_env "PUBLIC_SUPPORT_EMAIL" "$ADMIN_EMAIL"
fi

# Security: Ensure PSP/PIX are disabled (assuming manual billing covers this)
# If there were specific variables, we'd set them here.
# For now, explicit local appliance settings:
update_env "PUBLIC_EXPOSURE" "false"
update_env "PUBLIC_SIGNUP_ENABLED" "false"

# Ensure ADMIN_TOKEN exists and is secure
ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" "$ENV_FILE" | cut -d '=' -f2 || echo "")
if [[ -z "$ADMIN_TOKEN" || "$ADMIN_TOKEN" == "ChangeMe_ProdAdminToken_2026!" || "$ADMIN_TOKEN" == "default-admin-token" || "$ADMIN_TOKEN" == "default-token" || "$ADMIN_TOKEN" == "change-me" ]]; then
  log "Generating secure ADMIN_TOKEN..."
  NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  update_env "ADMIN_TOKEN" "$NEW_TOKEN"
  ADMIN_TOKEN="$NEW_TOKEN"
fi

chmod 600 "$ENV_FILE"

# 7. Generate Summary Files
SUMMARY_JSON="${SUMMARY_DIR}/configuration-summary.json"
SUMMARY_MD="${SUMMARY_DIR}/configuration-summary.md"

MASKED_TOKEN=$(mask_token "$ADMIN_TOKEN")

cat <<EOF > "$SUMMARY_JSON"
{
  "version": "${VERSION}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "base_url": "$BASE_URL",
  "host_port": "$HOST_PORT",
  "gpu_enabled": $GPU,
  "demo_mode": $ENABLE_DEMO,
  "admin_email": "${ADMIN_EMAIL:-"N/A"}",
  "admin_token_masked": "$MASKED_TOKEN",
  "local_appliance_mode": true,
  "local_billing_mode": "manual"
}
EOF

cat <<EOF > "$SUMMARY_MD"
# Configuration Summary - Local Appliance
Generated on: $(date)

- **Version:** ${VERSION}
- **Base URL:** $BASE_URL
- **Host Port:** $HOST_PORT
- **GPU Enabled:** $GPU
- **Demo Mode:** $ENABLE_DEMO
- **Admin Email:** ${ADMIN_EMAIL:-"N/A"}
- **Admin Token:** \`$MASKED_TOKEN\` (Stored securely in .env.local)
- **Local Appliance Mode:** Active
- **Local Billing Mode:** Manual (Real PSP/PIX disabled)

## Next Steps
1. Verify models in \`$MODELS_PATH\`
2. Run \`make install-local\` or \`./scripts/install-local-appliance.sh\`
3. Access the dashboard at $BASE_URL/admin
EOF

log "Configuration complete!"
operator_success "Configuração do assistente local concluída!"

add_next_step "Verifique os modelos em \`$MODELS_PATH\`"
add_next_step "Execute \`make install-local\` ou \`./scripts/install-local-appliance.sh\`"
add_next_step "Acesse o dashboard em $BASE_URL/admin"

print_next_steps

if ask_confirm "Would you like to create a demo client now?" "n"; then
  log "Demo client creation will be handled by the main installer or manual command."
  echo "Command: ./scripts/create-customer-demo.sh"
fi

exit 0
