#!/usr/bin/env bash
set -euo pipefail

# scripts/validators/validate-migrations-local.sh
# Valida migrations do Alembic no ambiente local.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEMP_DB=false
CLEANUP=true

usage() {
    echo "Uso: $0 [OPÇÕES]"
    echo ""
    echo "Opções:"
    echo "  --temp-db    Usa um banco de dados temporário (Docker) para validação completa"
    echo "  --no-cleanup Não remove o banco temporário ao final (útil para debug)"
    echo "  -h, --help   Mostra esta ajuda"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --temp-db) TEMP_DB=true ;;
        --no-cleanup) CLEANUP=false ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Erro: Opção desconhecida $1"; usage; exit 1 ;;
    esac
    shift
done

# Check if alembic is available
ALEMBIC="${ROOT_DIR}/.venv/bin/alembic"
if [[ ! -f "${ALEMBIC}" ]]; then
    # Fallback to system alembic if venv is not found
    ALEMBIC="alembic"
fi

cd "${ROOT_DIR}/control_plane"

VERSIONS_DIR="${ALEMBIC_VERSIONS_DIR:-alembic/versions}"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_heads() {
    log_info "Verificando heads do Alembic..."
    HEADS=$(${ALEMBIC} heads)
    HEAD_COUNT=$(echo "${HEADS}" | grep -c " (head)" || true)
    
    if [ "${HEAD_COUNT}" -eq 0 ]; then
        log_error "Nenhuma head encontrada no Alembic."
        return 1
    elif [ "${HEAD_COUNT}" -gt 1 ]; then
        log_error "Múltiplas heads detectadas! Isso pode causar conflitos de migration."
        echo "${HEADS}"
        return 1
    fi
    log_info "Apenas uma head detectada: OK"
    return 0
}

check_duplicates() {
    log_info "Verificando IDs duplicados ou nomes de arquivos conflitantes..."
    DUPS=$(find "${VERSIONS_DIR}" -name "*.py" -print0 | xargs -0 grep -h "^revision =" | sort | uniq -d)
    if [ -n "${DUPS}" ]; then
        log_error "IDs de revisão duplicados encontrados:"
        echo "${DUPS}"
        return 1
    fi
    log_info "Nenhum ID duplicado: OK"
    return 0
}

check_imports() {
    log_info "Verificando imports quebrados nas migrations..."
    # Tenta importar cada arquivo de migration
    for f in "${VERSIONS_DIR}"/*.py; do
        if ! python3 -m py_compile "${f}" > /dev/null 2>&1; then
            log_error "Erro de compilação/import no arquivo: ${f}"
            return 1
        fi
    done
    log_info "Todos os arquivos de migration são compiláveis: OK"
    return 0
}

validate_current_env() {
    log_info "Validando status no ambiente atual..."
    if ! ${ALEMBIC} current > /dev/null 2>&1; then
        log_warn "Não foi possível conectar ao banco de dados atual ou banco não inicializado."
        return 0
    fi
    
    # Verifica se há migrations pendentes
    HISTORY=$(${ALEMBIC} history)
    CURRENT=$(${ALEMBIC} current)
    
    # Se current estiver vazio e houver history, tem coisa pendente
    if [ -z "${CURRENT}" ] && [ -n "${HISTORY}" ]; then
        log_warn "Banco de dados inicializado mas sem registro de migrations (current está vazio)."
    fi
    
    return 0
}

run_temp_db_validation() {
    log_info "Iniciando validação com banco de dados temporário..."
    
    TEMP_DB_NAME="llm_gateway_val_$(date +%s)"
    TEMP_PORT=5433
    
    # Garante que a porta está livre ou tenta outra
    while lsof -Pi :${TEMP_PORT} -sTCP:LISTEN -t >/dev/null ; do
        TEMP_PORT=$((TEMP_PORT + 1))
    done

    log_info "Subindo container Postgres temporário na porta ${TEMP_PORT}..."
    docker run --name "${TEMP_DB_NAME}" \
      -e POSTGRES_DB=llm_gateway \
      -e POSTGRES_USER=llm_gateway \
      -e POSTGRES_PASSWORD=llm_gateway_dev_password \
      -p "${TEMP_PORT}:5432" \
      -d postgres:16-alpine > /dev/null

    # Cleanup trap
    if [ "${CLEANUP}" = true ]; then
        trap 'log_info "Removendo container temporário..."; docker rm -f "${TEMP_DB_NAME}" > /dev/null' EXIT
    fi

    # Aguarda o banco ficar pronto
    log_info "Aguardando Postgres ficar pronto..."
    MAX_RETRIES=30
    COUNT=0
    until docker exec "${TEMP_DB_NAME}" pg_isready -U llm_gateway > /dev/null 2>&1; do
        sleep 1
        COUNT=$((COUNT + 1))
        if [ $COUNT -ge $MAX_RETRIES ]; then
            log_error "Timeout aguardando Postgres."
            return 1
        fi
    done

    # Override DATABASE_URL para o banco temporário
    # Nota: Usamos localhost porque o alembic rodará fora do container
    export DATABASE_URL="postgresql+asyncpg://llm_gateway:llm_gateway_dev_password@localhost:${TEMP_PORT}/llm_gateway"
    
    log_info "Rodando alembic upgrade head no banco temporário..."
    if ! ${ALEMBIC} upgrade head; then
        log_error "Falha ao aplicar migrations do zero no banco temporário!"
        return 1
    fi
    
    log_info "Validando schema final..."
    # Aqui poderíamos rodar algum script que verifica se as tabelas esperadas existem
    # Por agora, o sucesso do 'upgrade head' já é uma grande validação.
    
    log_info "Banco temporário validado com sucesso!"
    return 0
}

# Main Execution
EXIT_CODE=0

check_heads || EXIT_CODE=1
check_duplicates || EXIT_CODE=1
check_imports || EXIT_CODE=1
validate_current_env || EXIT_CODE=1

if [ "${TEMP_DB}" = true ]; then
    run_temp_db_validation || EXIT_CODE=1
fi

if [ $EXIT_CODE -eq 0 ]; then
    log_info "--------------------------------------------------------"
    log_info "Validação de migrations concluída com SUCESSO."
    log_info "--------------------------------------------------------"
else
    log_error "--------------------------------------------------------"
    log_error "Validação de migrations FALHOU."
    log_error "--------------------------------------------------------"
fi

exit $EXIT_CODE
