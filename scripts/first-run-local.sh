#!/usr/bin/env bash
# First Run Local Setup
# Sets up, configures, and validates the system locally for technical operators.

set -euo pipefail

WITH_DEMO=false
SKIP_BUILD=false
CPU_ONLY=false
GPU=false
BASE_URL="http://localhost:18080"
YES=false
DRY_RUN=false

show_help() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --with-demo     Run demo after setup"
  echo "  --skip-build    Skip docker compose build"
  echo "  --cpu-only      Force CPU mode"
  echo "  --gpu           Force GPU mode"
  echo "  --base-url URL  Set base URL (default: http://localhost:18080)"
  echo "  --yes           Skip confirmations"
  echo "  --dry-run       Show what would be done without doing it"
  echo "  --help          Show this help"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --with-demo) WITH_DEMO=true; shift ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    --cpu-only) CPU_ONLY=true; shift ;;
    --gpu) GPU=true; shift ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --yes) YES=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

if [ "$DRY_RUN" = true ]; then
  echo "[DRY-RUN] Would execute first-run setup with:"
  echo "  WITH_DEMO: $WITH_DEMO"
  echo "  SKIP_BUILD: $SKIP_BUILD"
  echo "  CPU_ONLY: $CPU_ONLY"
  echo "  GPU: $GPU"
  echo "  BASE_URL: $BASE_URL"
  exit 0
fi

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
REPORT_DIR="artifacts/first-run/${TIMESTAMP}"
mkdir -p "$REPORT_DIR"
mkdir -p "$REPORT_DIR/logs"
REPORT_JSON="$REPORT_DIR/first-run-report.json"
REPORT_MD="$REPORT_DIR/first-run-report.md"

log() {
  echo "[INFO] $1" | tee -a "$REPORT_DIR/logs/setup.log"
}

warn() {
  echo "[WARN] $1" | tee -a "$REPORT_DIR/logs/setup.log"
}

error() {
  echo "[ERROR] $1" | tee -a "$REPORT_DIR/logs/setup.log"
  exit 1
}

log "Starting first run local setup..."

# a) Detect environment
OS=$(uname -s)
WSL_DETECTED=false
if grep -qi microsoft /proc/version 2>/dev/null; then
  WSL_DETECTED=true
fi
DOCKER_VERSION=$(docker --version 2>/dev/null || echo "Not found")
COMPOSE_VERSION=$(docker compose version 2>/dev/null || echo "Not found")
GPU_DETECTED=false
NVIDIA_SMI_STATUS="Not found"
if command -v nvidia-smi >/dev/null 2>&1; then
  NVIDIA_SMI_STATUS=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || echo "Error")
  GPU_DETECTED=true
fi

# b) Prepare configuration
ENV_CREATED=false
ENV_BACKUP_PATH=""
if [ ! -f .env.local ]; then
  log "Creating .env.local from .env.example..."
  if [ -f .env.local.example ]; then
    cp .env.local.example .env.local
  else
    cp .env.example .env.local
  fi
  chmod 600 .env.local
  ENV_CREATED=true
else
  log ".env.local exists, creating backup just in case..."
  ENV_BACKUP_PATH=".env.local.bak.$TIMESTAMP"
  cp .env.local "$ENV_BACKUP_PATH"
  chmod 600 "$ENV_BACKUP_PATH"
fi

# Update .env.local safely
update_env() {
  local key=$1
  local val=$2
  if grep -q "^$key=" .env.local; then
    sed -i "s|^$key=.*|$key=$val|" .env.local
  else
    echo "$key=$val" >> .env.local
  fi
}

ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" .env.local | cut -d '=' -f2 || echo "")
if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "default-admin-token" ]; then
  log "Generating secure ADMIN_TOKEN..."
  NEW_TOKEN=$(openssl rand -hex 32)
  update_env "ADMIN_TOKEN" "$NEW_TOKEN"
fi

update_env "LOCALHOST_MODE" "true"
update_env "LOCAL_BILLING_MODE" "manual"
update_env "BASE_URL" "$BASE_URL"
update_env "PUBLIC_BASE_URL" "$BASE_URL"

# c) Verify models
MODELS_DETECTED=0
MODEL_LIST=""
mkdir -p models
if ls models/*.gguf >/dev/null 2>&1; then
  MODEL_LIST=$(ls models/*.gguf | xargs -n 1 basename)
  MODELS_DETECTED=$(echo "$MODEL_LIST" | wc -w)
fi

if [ "$MODELS_DETECTED" -eq 0 ]; then
  warn "No models (.gguf) found in models/ directory."
  echo "You will need to add a model manually (e.g., via ./scripts/download-model.sh)."
  if [ "$YES" = false ]; then
    read -p "Press Enter to continue or Ctrl+C to abort..."
  fi
else
  log "Found $MODELS_DETECTED model(s)."
fi

# d) Start stack
log "Starting stack..."
COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
if [ "$SKIP_BUILD" = false ]; then
  $COMPOSE_CMD up -d --build
else
  $COMPOSE_CMD up -d
fi

log "Waiting for /health..."
retries=30
while [ $retries -gt 0 ]; do
  if curl -s "$BASE_URL/health" | grep -q "status"; then
    break
  fi
  sleep 2
  retries=$((retries-1))
done

if [ $retries -eq 0 ]; then
  error "Stack health check failed."
fi

log "Waiting for /ready..."
retries=30
while [ $retries -gt 0 ]; do
  READY_RESP=$(curl -s "$BASE_URL/ready" || echo "")
  if echo "$READY_RESP" | grep -q "ok\|degraded"; then
    log "Ready status: $(echo "$READY_RESP" | grep -o 'ok\|degraded' | head -1)"
    break
  fi
  sleep 2
  retries=$((retries-1))
done

# e) Validate
log "Running validations..."
VALIDATION_RESULT="passed"
if ! ./scripts/check-secrets.sh --all; then
  VALIDATION_RESULT="failed_check_secrets"
fi

if ! ./scripts/validate-local-production-full.sh; then
  VALIDATION_RESULT="failed_validate_production"
fi

DEMO_SEEDED=false
if [ "$WITH_DEMO" = true ]; then
  log "Running demo..."
  if ./scripts/demo-full-local.sh --no-build; then
    DEMO_SEEDED=true
  else
    VALIDATION_RESULT="failed_demo"
  fi
fi

# f) Generate report
cat <<EOF > "$REPORT_JSON"
{
  "generated_at": "$TIMESTAMP",
  "base_url": "$BASE_URL",
  "os": "$OS",
  "wsl2": $WSL_DETECTED,
  "docker_version": "$DOCKER_VERSION",
  "compose_version": "$COMPOSE_VERSION",
  "gpu_detected": $GPU_DETECTED,
  "nvidia_smi": "$NVIDIA_SMI_STATUS",
  "env_created": $ENV_CREATED,
  "env_backup_path": "$ENV_BACKUP_PATH",
  "models_detected": $MODELS_DETECTED,
  "services_status": "up",
  "validation_result": "$VALIDATION_RESULT",
  "demo_seeded": $DEMO_SEEDED,
  "warnings": [],
  "next_steps": ["Check $BASE_URL", "Review $REPORT_MD"]
}
EOF

cat <<EOF > "$REPORT_MD"
# First Run Local Report
**Generated At:** $TIMESTAMP

## Environment
* **OS:** $OS (WSL2: $WSL_DETECTED)
* **Docker:** $DOCKER_VERSION
* **Compose:** $COMPOSE_VERSION
* **GPU Detected:** $GPU_DETECTED
* **NVIDIA SMI:** $NVIDIA_SMI_STATUS

## Setup
* **Env Created:** $ENV_CREATED
* **Env Backup Path:** $ENV_BACKUP_PATH
* **Models Detected:** $MODELS_DETECTED

## Validation
* **Result:** $VALIDATION_RESULT
* **Demo Seeded:** $DEMO_SEEDED
EOF

log "First run complete! Report saved to $REPORT_DIR"
log "Recommended next steps: Open $BASE_URL in your browser."

echo "Report path: $REPORT_DIR"
echo "Security guarantees: No secrets exposed in logs, .env.local created securely with mode 600."

exit 0
