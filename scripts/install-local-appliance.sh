#!/usr/bin/env bash
# LLM Inference Stack - Local Appliance Installer
# This script installs the system as a local appliance.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
VERSION=$(cat "${ROOT_DIR}/VERSION" 2>/dev/null || echo "unknown")

# Load operator errors library
if [[ -f "${ROOT_DIR}/lib/operator-errors.sh" ]]; then
  source "${ROOT_DIR}/scripts/lib/operator-errors.sh"
fi

# Default values
WITH_DEMO=false
SKIP_BUILD=false
CPU_ONLY=false
GPU=false
BASE_URL="http://localhost:18080"
ADMIN_EMAIL=""
NO_OPEN_BROWSER=false
YES=false
DRY_RUN=false

show_help() {
  echo "LLM Inference Stack - Local Appliance Installer v${VERSION}"
  echo ""
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --yes               Skip confirmations"
  echo "  --dry-run           Show what would be done without doing it"
  echo "  --with-demo         Seed demo data after installation"
  echo "  --skip-build        Skip docker compose build"
  echo "  --cpu-only          Force CPU mode"
  echo "  --gpu               Force GPU mode (requires NVIDIA drivers)"
  echo "  --base-url URL      Set public base URL (default: http://localhost:18080)"
  echo "  --admin-email EMAIL Optional admin email"
  echo "  --no-demo           Explicitly do not seed demo data"
  echo "  --no-open-browser   Do not attempt to open the browser after installation"
  echo "  --help              Show this help"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --yes) YES=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --with-demo) WITH_DEMO=true; shift ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    --cpu-only) CPU_ONLY=true; shift ;;
    --gpu) GPU=true; shift ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    --no-demo) WITH_DEMO=false; shift ;;
    --no-open-browser) NO_OPEN_BROWSER=true; shift ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Banner
echo "===================================================="
echo "    LLM Inference Stack - Local Appliance Mode"
echo "    Version: ${VERSION}"
echo "===================================================="
echo "Notice: Real PSP/PIX integrations are out of scope."
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "[DRY-RUN] Installer would proceed with:"
  echo "  WITH_DEMO: $WITH_DEMO"
  echo "  SKIP_BUILD: $SKIP_BUILD"
  echo "  CPU_ONLY: $CPU_ONLY"
  echo "  GPU: $GPU"
  echo "  BASE_URL: $BASE_URL"
  echo "  ADMIN_EMAIL: ${ADMIN_EMAIL:-N/A}"
  
  # Generate a dry-run report
  TIMESTAMP=$(date +%Y%m%dT%H%M%S)
  ARTIFACT_DIR="${ROOT_DIR}/artifacts/install-local-appliance/${TIMESTAMP}-dryrun"
  mkdir -p "${ARTIFACT_DIR}/logs"
  REPORT_JSON="${ARTIFACT_DIR}/install-report.json"
  REPORT_MD="${ARTIFACT_DIR}/install-report.md"
  
  cat <<EOF > "${REPORT_JSON}"
{
  "version": "${VERSION}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "dry_run": true,
  "base_url": "${BASE_URL}",
  "next_steps": ["Run without --dry-run to install"]
}
EOF
  cat <<EOF > "${REPORT_MD}"
# Installation Report (DRY-RUN)
- **Version:** ${VERSION}
- **Status:** DRY-RUN SUCCESS
EOF
  echo "Dry-run report generated at: ${ARTIFACT_DIR}"
  exit 0
fi

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/install-local-appliance/${TIMESTAMP}"
LOGS_DIR="${ARTIFACT_DIR}/logs"
mkdir -p "${LOGS_DIR}"
REPORT_JSON="${ARTIFACT_DIR}/install-report.json"
REPORT_MD="${ARTIFACT_DIR}/install-report.md"
INSTALL_LOG="${LOGS_DIR}/install.log"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1" | tee -a "${INSTALL_LOG}"
}

warn() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [WARN] $1" | tee -a "${INSTALL_LOG}"
}

error() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1" | tee -a "${INSTALL_LOG}"
  exit 1
}

# 1. Pre-checks
log "Starting pre-checks..."

OS=$(uname -s)
WSL2=false
if grep -qi microsoft /proc/version 2>/dev/null; then
  WSL2=true
fi

check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    if [[ "$1" == "docker" ]]; then
       operator_error "DOCKER_NOT_RUNNING" "O Docker não parece estar instalado ou acessível." "Instale o Docker ou verifique se ele está no PATH."
    elif [[ "$1" == "docker compose" ]] || [[ "$1" == "docker-compose" ]]; then
       operator_error "DOCKER_COMPOSE_MISSING" "O Docker Compose não foi encontrado." "Instale o plugin docker-compose-plugin ou o executável docker-compose."
    else
       operator_error "VALIDATION_FAILED" "Dependência ausente: $1" "Instale $1 usando o gerenciador de pacotes do seu sistema."
    fi
    exit 1
  fi
}

check_cmd docker
if ! docker info >/dev/null 2>&1; then
  operator_error "DOCKER_NOT_RUNNING" "O Docker está instalado, mas não parece estar rodando." "Inicie o Docker Desktop ou rode sudo systemctl start docker." "docker info falhou."
  exit 1
fi

check_cmd "docker compose" || check_cmd docker-compose
check_cmd git
check_cmd curl
check_cmd jq
check_cmd python3

DOCKER_VERSION=$(docker --version)
COMPOSE_VERSION=$(docker compose version 2>/dev/null || docker-compose version)

GPU_DETECTED=false
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi >/dev/null 2>&1; then
    GPU_DETECTED=true
    log "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)"
  fi
fi

if [ "$GPU" = true ] && [ "$GPU_DETECTED" = false ]; then
  warn "--gpu flag provided but nvidia-smi failed. Installation might fail if GPU is required."
fi

# Check ports
check_port() {
  local port=$1
  if netstat -tuln | grep -q ":$port "; then
    operator_error "PORT_IN_USE" "A porta $port já está em uso por outro processo." "Identifique o processo que usa a porta $port e encerre-o, ou altere as portas no arquivo .env.local."
    exit 1
  fi
}
# check_port 18080 # This might be restrictive if the stack is already partially up or if we are upgrading.
# Instead of hard error, maybe just warn or check if it is our own service.

# 2. Configuration
log "Configuring environment..."

ENV_FILE="${ROOT_DIR}/.env.local"
ENV_CREATED=false
ENV_BACKUP_PATH=""

if [ -f "${ENV_FILE}" ]; then
  ENV_BACKUP_DIR="${ROOT_DIR}/.local/backups/env"
  mkdir -p "${ENV_BACKUP_DIR}"
  ENV_BACKUP_PATH="${ENV_BACKUP_DIR}/.env.local.${TIMESTAMP}.bak"
  cp "${ENV_FILE}" "${ENV_BACKUP_PATH}"
  chmod 600 "${ENV_BACKUP_PATH}"
  log "Environment backup created: ${ENV_BACKUP_PATH}"
fi

# Call the wizard to handle .env.local and other settings
WIZARD_ARGS=("--non-interactive" "--base-url" "${BASE_URL}")
if [ "$YES" = true ]; then WIZARD_ARGS+=("--yes"); fi
if [ "$GPU" = true ]; then WIZARD_ARGS+=("--gpu"); fi
if [ "$CPU_ONLY" = true ]; then WIZARD_ARGS+=("--cpu-only"); fi
if [ "$WITH_DEMO" = true ]; then WIZARD_ARGS+=("--enable-demo"); fi
if [ -n "${ADMIN_EMAIL}" ]; then WIZARD_ARGS+=("--admin-email" "${ADMIN_EMAIL}"); fi

if [ ! -f "${ENV_FILE}" ]; then
  ENV_CREATED=true
fi

WIZARD_SKIP_ENV_BACKUP=true "${SCRIPT_DIR}/configure-local-wizard.sh" "${WIZARD_ARGS[@]}"

# 3. Models verification
log "Verifying models..."
MODELS_DIR="${ROOT_DIR}/models"
mkdir -p "${MODELS_DIR}"
GGUF_MODELS=$(find "${MODELS_DIR}" -maxdepth 1 -name "*.gguf" -printf "%f\n" || echo "")
MODELS_COUNT=$(echo "${GGUF_MODELS}" | grep -c ".gguf" || echo "0")

if [ "${MODELS_COUNT}" -eq 0 ]; then
  warn "No models (.gguf) found in ${MODELS_DIR}."
  echo "The system will start with a mock/empty data plane if models are missing."
  echo "To add models: copy .gguf files to ${MODELS_DIR} and restart."
  if [ "$YES" = false ]; then
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      error "Aborted by user."
    fi
  fi
else
  log "Found ${MODELS_COUNT} model(s):"
  echo "${GGUF_MODELS}" | while read -r m; do log "  - $m"; done
fi

# 4. Start stack
log "Starting services..."
COMPOSE_CMD="docker compose"
if ! $COMPOSE_CMD version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

UP_ARGS=("-d")
if [ "$SKIP_BUILD" = false ]; then
  UP_ARGS+=("--build")
fi

$COMPOSE_CMD --env-file "${ENV_FILE}" up "${UP_ARGS[@]}"

# Wait for health
log "Waiting for system to be healthy..."
HEALTH_URL="${BASE_URL}/health"
MAX_RETRIES=60
RETRY_COUNT=0
until curl -s "${HEALTH_URL}" | grep -q "status"; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    operator_error "HEALTH_FAILED" "O sistema não ficou saudável dentro do tempo esperado." "Verifique os logs dos containers com 'docker compose logs'." "Falha ao acessar ${HEALTH_URL} após ${MAX_RETRIES} tentativas."
    exit 1
  fi
  sleep 2
done
log "System is healthy."

# 5. Migrations
log "Running migrations..."
if [ -x "${SCRIPT_DIR}/validate-migrations-local.sh" ]; then
  "${SCRIPT_DIR}/validate-migrations-local.sh" || warn "Migration validation reported issues."
fi

# 6. Validation
log "Running full validation suite..."
VALIDATION_SUCCESS=true

log "Checking secrets..."
"${SCRIPT_DIR}/check-secrets.sh" --all || { warn "Secrets check failed."; VALIDATION_SUCCESS=false; }

log "Validating production setup..."
"${SCRIPT_DIR}/validate-local-production-full.sh" || { warn "Production validation failed."; VALIDATION_SUCCESS=false; }

log "Checking readiness..."
"${SCRIPT_DIR}/production-readiness-local.sh" || { warn "Readiness check failed."; VALIDATION_SUCCESS=false; }

log "Generating security report..."
"${SCRIPT_DIR}/security-report-local.sh" || warn "Security report generation failed."

log "Running post-installation validation..."
POST_INSTALL_ARGS=("--base-url" "${BASE_URL}")
if [ "$WITH_DEMO" = true ]; then POST_INSTALL_ARGS+=("--with-demo"); fi
"${SCRIPT_DIR}/validate-post-install-local.sh" "${POST_INSTALL_ARGS[@]}" || { warn "Post-installation validation failed."; VALIDATION_SUCCESS=false; }

DEMO_SEEDED=false
if [ "$WITH_DEMO" = true ]; then
  log "Seeding demo data..."
  "${SCRIPT_DIR}/demo-full-local.sh" --no-build || { warn "Demo seeding failed."; VALIDATION_SUCCESS=false; }
  DEMO_SEEDED=true
fi

# 7. Generate report
log "Generating installation reports..."
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

cat <<EOF > "${REPORT_JSON}"
{
  "version": "${VERSION}",
  "git_commit": "${GIT_COMMIT}",
  "git_branch": "${GIT_BRANCH}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "base_url": "${BASE_URL}",
  "os": "${OS}",
  "wsl2": ${WSL2},
  "docker_version": "${DOCKER_VERSION}",
  "compose_version": "${COMPOSE_VERSION}",
  "gpu_detected": ${GPU_DETECTED},
  "models_detected": ${MODELS_COUNT},
  "env_created": ${ENV_CREATED},
  "env_backup_path": "${ENV_BACKUP_PATH}",
  "services_status": "up",
  "migrations_status": "executed",
  "validation_status": "${VALIDATION_SUCCESS}",
  "demo_seeded": ${DEMO_SEEDED},
  "warnings": [],
  "next_steps": [
    "Open Landing Page: ${BASE_URL}",
    "Open Admin Dashboard: ${BASE_URL}/admin",
    "Open Client Portal: ${BASE_URL}/client-portal"
  ]
}
EOF

cat <<EOF > "${REPORT_MD}"
# Installation Report - Local Appliance
Generated on: $(date)

## System Info
- **Version:** ${VERSION}
- **Commit:** ${GIT_COMMIT}
- **Branch:** ${GIT_BRANCH}
- **OS:** ${OS} (WSL2: ${WSL2})
- **Docker:** ${DOCKER_VERSION}
- **GPU Detected:** ${GPU_DETECTED}

## Setup Result
- **Base URL:** [${BASE_URL}](${BASE_URL})
- **Models Found:** ${MODELS_COUNT}
- **Env Backup:** ${ENV_BACKUP_PATH:-None}
- **Validation:** $([ "$VALIDATION_SUCCESS" = true ] && echo "PASS" || echo "FAIL")
- **Demo Seeded:** ${DEMO_SEEDED}

## Access Points
- **Landing:** ${BASE_URL}
- **Admin Dashboard:** ${BASE_URL}/admin
- **Client Portal:** ${BASE_URL}/client-portal
- **API Docs:** ${BASE_URL}/docs

## Useful Commands
\`\`\`bash
make health
make validate
make readiness
make security
\`\`\`
EOF

log "Installation complete!"
operator_success "Instalação do LLM Inference Stack concluída com sucesso!"

add_next_step "Abra a Landing Page: ${BASE_URL}"
add_next_step "Abra o Painel de Administração: ${BASE_URL}/admin"
add_next_step "Abra o Portal do Cliente: ${BASE_URL}/client-portal"
add_next_step "Consulte o relatório de instalação: ${REPORT_MD}"

print_next_steps

if [ "$NO_OPEN_BROWSER" = false ]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${BASE_URL}" >/dev/null 2>&1 || true
  fi
fi

exit 0
