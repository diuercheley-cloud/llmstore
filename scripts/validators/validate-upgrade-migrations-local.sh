#!/usr/bin/env bash
set -euo pipefail

# scripts/validators/validate-upgrade-migrations-local.sh
# Simula e valida o processo de upgrade de migrations com segurança.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Uso: $0 [OPÇÕES]"
    echo ""
    echo "Opções:"
    echo "  -h, --help   Mostra esta ajuda"
    echo ""
    echo "Este script simula o fluxo completo de upgrade para validar migrations."
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "--------------------------------------------------------"
echo "Simulação de Upgrade de Migrations"
echo "--------------------------------------------------------"

# 1. Backup de Segurança
log_info "Passo 1: Criando backup de segurança antes do upgrade..."
if ! ./scripts/backup/backup-local.sh; then
    log_error "Falha ao criar backup. Abortando validação por segurança."
    exit 1
fi

# 2. Validação Estática de Migrations
log_info "Passo 2: Rodando validação estática de migrations..."
if ! ./scripts/validators/validate-migrations-local.sh; then
    log_error "Validação estática falhou. Corrija as migrations antes de prosseguir."
    exit 1
fi

# 3. Upgrade de Migrations
log_info "Passo 3: Executando upgrade head no control-plane..."
if ! dc exec -T control-plane alembic upgrade head; then
    log_error "Erro ao executar alembic upgrade head."
    exit 1
fi

# 4. Verificação de Saúde (Health Check)
log_info "Passo 4: Verificando saúde dos serviços..."
if ! dc ps | grep "control-plane" | grep -q "(healthy)"; then
    log_warn "Control-plane não reportou status healthy. Aguardando 10s..."
    sleep 10
    if ! dc ps | grep "control-plane" | grep -q "(healthy)"; then
        log_error "Control-plane continua instável após upgrade."
        exit 1
    fi
fi
log_info "Serviços estão saudáveis: OK"

# 5. Smoke Test Mínimo
log_info "Passo 5: Rodando smoke test mínimo..."
BASE_URL=$(default_base_url)
# Verifica se a API responde
if ! curl -fsS "${BASE_URL}/health" > /dev/null 2>&1; then
    log_error "API não responde em ${BASE_URL}/health"
    exit 1
fi
log_info "API respondendo: OK"

log_info "--------------------------------------------------------"
log_info "Validação de UPGRADE concluída com SUCESSO."
log_info "--------------------------------------------------------"
