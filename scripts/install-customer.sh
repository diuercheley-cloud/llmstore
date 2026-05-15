#!/usr/bin/env bash
# LLM Inference Stack - Professional Customer Installer Wizard
# Designed for client-side installations with distinct product profiles.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "1.8.1-customer")

# Load libraries
source "${SCRIPT_DIR}/lib/operator-errors.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/validation-logging.sh" 2>/dev/null || true

# Colors for terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global Config
ENV_CUSTOMER="${ROOT_DIR}/.env.customer"
ENV_LOCAL="${ROOT_DIR}/.env.local"
BACKUP_DIR="${ROOT_DIR}/.local/backups/customer"
LOG_FILE="${ROOT_DIR}/logs/install-customer.log"

mkdir -p "${ROOT_DIR}/logs"
mkdir -p "${BACKUP_DIR}"

log_header() {
  echo -e "\n${BLUE}====================================================${NC}"
  echo -e "${BLUE}    LLM Inference Stack - Customer Installer        ${NC}"
  echo -e "${BLUE}    Version: ${VERSION}                             ${NC}"
  echo -e "${BLUE}====================================================${NC}\n"
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Helper to update env file
update_env() {
  local key=$1
  local val=$2
  local file=$3
  if grep -q "^$key=" "$file"; then
    local escaped_val=$(echo "$val" | sed 's/[&/\]/\\&/g')
    sed -i "s|^$key=.*|$key=$escaped_val|" "$file"
  else
    echo "$key=$val" >> "$file"
  fi
}

# --- 1. Profile Selection ---
select_profile() {
  if [ -n "${1:-}" ]; then
    case $1 in
      appliance-local|hybrid-provider|demo-sales|enterprise-rag|dev-lab)
        PROFILE=$1
        return
        ;;
      *) log_error "Invalid profile: $1" ;;
    esac
  fi

  echo "Select a product profile:"
  echo "1) appliance-local   (Local-first, air-gapped capable, no cloud)"
  echo "2) hybrid-provider   (Local + Cloud providers like OpenAI/Anthropic)"
  echo "3) demo-sales        (Optimized for sales demos with pre-seeded data)"
  echo "4) enterprise-rag    (Focus on RAG, heavy document processing)"
  echo "5) dev-lab           (Development and testing environment)"
  
  read -p "Choose profile [1-5]: " PROFILE_CHOICE
  case $PROFILE_CHOICE in
    1) PROFILE="appliance-local" ;;
    2) PROFILE="hybrid-provider" ;;
    3) PROFILE="demo-sales" ;;
    4) PROFILE="enterprise-rag" ;;
    5) PROFILE="dev-lab" ;;
    *) log_error "Invalid choice." ;;
  esac
  log_info "Selected Profile: $PROFILE"
}

# --- 2. Configuration Wizard ---
run_wizard() {
  log_info "Configuring $PROFILE stack..."

  # Common Configs
  read -p "Service Port [18080]: " HOST_PORT
  HOST_PORT=${HOST_PORT:-18080}

  read -p "Domain or Local IP [localhost]: " DOMAIN
  DOMAIN=${DOMAIN:-localhost}
  BASE_URL="http://${DOMAIN}:${HOST_PORT}"

  # Admin Config
  read -p "Admin Email [admin@example.com]: " ADMIN_EMAIL
  ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

  # Generate Token
  ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(24))")
  
  # Initialize .env.customer
  cp "${ROOT_DIR}/.env.example" "$ENV_CUSTOMER"
  chmod 600 "$ENV_CUSTOMER"

  # Apply Common Configs
  update_env "HOST_PORT" "$HOST_PORT" "$ENV_CUSTOMER"
  update_env "APP_PUBLIC_URL" "$BASE_URL" "$ENV_CUSTOMER"
  update_env "PUBLIC_BASE_URL" "$BASE_URL" "$ENV_CUSTOMER"
  update_env "ADMIN_BASE_URL" "${BASE_URL}/admin" "$ENV_CUSTOMER"
  update_env "CLIENT_PORTAL_BASE_URL" "${BASE_URL}/client-portal" "$ENV_CUSTOMER"
  update_env "ADMIN_TOKEN" "$ADMIN_TOKEN" "$ENV_CUSTOMER"
  update_env "ADMIN_EMAIL" "$ADMIN_EMAIL" "$ENV_CUSTOMER"
  update_env "PUBLIC_BRAND_NAME" "LLM Appliance ($PROFILE)" "$ENV_CUSTOMER"

  # Profile-Specific Configs
  case $PROFILE in
    appliance-local)
      update_env "REAL_PROVIDER_VALIDATION_ENABLED" "false" "$ENV_CUSTOMER"
      update_env "LOCALHOST_MODE" "true" "$ENV_CUSTOMER"
      update_env "RAG_ENABLED" "true" "$ENV_CUSTOMER"
      ;;
    hybrid-provider)
      update_env "REAL_PROVIDER_VALIDATION_ENABLED" "true" "$ENV_CUSTOMER"
      echo "Enable Cloud Providers?"
      if read -p "Enable OpenAI? [y/N]: " q && [[ $q =~ ^[Yy]$ ]]; then
        update_env "OPENAI_PROVIDER_ENABLED" "true" "$ENV_CUSTOMER"
        read -p "OpenAI API Key: " key
        update_env "OPENAI_API_KEY" "$key" "$ENV_CUSTOMER"
      fi
      if read -p "Enable Anthropic? [y/N]: " q && [[ $q =~ ^[Yy]$ ]]; then
        update_env "ANTHROPIC_PROVIDER_ENABLED" "true" "$ENV_CUSTOMER"
        read -p "Anthropic API Key: " key
        update_env "ANTHROPIC_API_KEY" "$key" "$ENV_CUSTOMER"
      fi
      ;;
    demo-sales)
      update_env "DEMO_MODE" "true" "$ENV_CUSTOMER"
      update_env "PUBLIC_SIGNUP_ENABLED" "true" "$ENV_CUSTOMER"
      ;;
    enterprise-rag)
      update_env "MAX_CONTEXT_TOKENS" "128000" "$ENV_CUSTOMER"
      update_env "RAG_ENABLED" "true" "$ENV_CUSTOMER"
      update_env "RAG_CHUNK_SIZE" "1500" "$ENV_CUSTOMER"
      ;;
    dev-lab)
      update_env "DEBUG" "true" "$ENV_CUSTOMER"
      update_env "LOG_LEVEL" "DEBUG" "$ENV_CUSTOMER"
      ;;
  esac

  # Feature Flags
  if read -p "Enable TTS? [y/N]: " q && [[ $q =~ ^[Yy]$ ]]; then
    update_env "TTS_ENABLED" "true" "$ENV_CUSTOMER"
  else
    update_env "TTS_ENABLED" "false" "$ENV_CUSTOMER"
  fi

  log_success "Created $ENV_CUSTOMER"
}

# --- 3. Deployment ---
deploy_stack() {
  log_info "Preparing deployment..."
  
  if [ -f "$ENV_LOCAL" ]; then
    log_warn "$ENV_LOCAL already exists. Creating backup..."
    cp "$ENV_LOCAL" "${BACKUP_DIR}/.env.local.$(date +%Y%m%d%H%M%S).bak"
  fi
  
  cp "$ENV_CUSTOMER" "$ENV_LOCAL"
  log_success "Applied configuration to $ENV_LOCAL"

  log_info "Starting Docker services..."
  # Use STACK_ENV_FILE if supported by Makefile, or just rely on .env.local
  make up

  log_info "Waiting for stack to be ready..."
  MAX_RETRIES=30
  COUNT=0
  until curl -s "${BASE_URL}/health" | grep -q "ok" || [ $COUNT -eq $MAX_RETRIES ]; do
    sleep 2
    COUNT=$((COUNT+1))
    echo -n "."
  done
  echo ""

  if [ $COUNT -eq $MAX_RETRIES ]; then
    log_error "Stack failed to start within timeout."
  fi
}

# --- 4. Post-Install Setup ---
post_install() {
  log_info "Running post-install setup..."
  
  # Create initial client and plan
  log_info "Creating initial customer and plan..."
  # Use scripts/create-plan.sh and scripts/create-client.sh with correct positional args
  # Usage: ./scripts/create-plan.sh CODE NAME [RPM] [DAILY] [WEEKLY] [MONTHLY] [MAX_TOKENS] [ALLOW_STREAMING] [DESCRIPTION]
  ./scripts/create-plan.sh "standard-plan" "Standard Plan" 20 100000 500000 2000000 2048 true "Plano inicial do cliente"
  
  CLIENT_NAME="Initial Customer"
  # Usage: ./scripts/create-client.sh CLIENT_NAME [DESCRIPTION]
  CLIENT_OUTPUT=$(./scripts/create-client.sh "$CLIENT_NAME" "Cliente criado via instalador")
  
  API_KEY=$(echo "$CLIENT_OUTPUT" | grep "api_key=" | cut -d'=' -f2 || echo "FAILED_TO_GET_KEY")
  
  if [ "$PROFILE" == "demo-sales" ]; then
    log_info "Seeding demo data..."
    make demo-pack
  fi

  log_success "Post-install setup complete."
  
  echo -e "\n${GREEN}====================================================${NC}"
  echo -e "${GREEN}    INSTALLATION SUCCESSFUL                         ${NC}"
  echo -e "${GREEN}====================================================${NC}"
  echo -e "Profile: $PROFILE"
  echo -e "Base URL: $BASE_URL"
  echo -e "Admin Token: ${YELLOW}${ADMIN_TOKEN}${NC} (DO NOT LOSE THIS)"
  echo -e "Initial Customer API Key: ${YELLOW}${API_KEY}${NC}"
  echo -e "Documentation: docs/CUSTOMER_INSTALL_WIZARD.md"
  echo -e "====================================================\n"
}

# Main Execution
log_header
select_profile "${1:-}"
run_wizard

if read -p "Proceed with deployment? [y/N]: " q && [[ $q =~ ^[Yy]$ ]]; then
  deploy_stack
  post_install
else
  log_info "Installation aborted by user. Config saved in $ENV_CUSTOMER"
fi
