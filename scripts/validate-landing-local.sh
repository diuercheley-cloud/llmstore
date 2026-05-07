#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

echo "--- Verificando Landing Page em ${BASE_URL} ---"
landing_content=$(curl_base_url "${BASE_URL}/" -fsS)

# Verificar textos principais
check_text() {
    if echo "${landing_content}" | grep -q "$1"; then
        echo "OK: Encontrado '$1'"
    else
        echo "FAIL: Não encontrado '$1'"
        exit 1
    fi
}

check_text "LLM Local para Empresas"
check_text "API compatível com OpenAI"
check_text "RAG com documentos internos"
check_text "Controle de Clientes e Uso"
check_text "Admin Lab p/ Modelos Locais"
check_text "Operação em Localhost"

# Verificar links locais
check_text "href=\"/admin/\""
check_text "href=\"/portal/\""
check_text "href=\"/docs\""

# Verificar Casos de Uso
check_text "Casos de Uso"
check_text "Escritórios e Consultoria"
check_text "Imobiliárias e Contabilidade"

# Verificar CTAs
check_text "Abrir Admin Dashboard"
check_text "Abrir Client Portal"
check_text "Ver Documentação"
check_text "Rodar validação local"

# Garantir que não há promessas de PIX real/PSP real ativo
if echo "${landing_content}" | grep -iE "PIX real|PSP real" | grep -v "Fora do escopo"; then
    echo "FAIL: Encontrada promessa de PIX/PSP real fora da seção de limitações!"
    exit 1
else
    echo "OK: Nenhuma promessa indevida de pagamentos reais."
fi

echo "VALIDAÇÃO DA LANDING PAGE LOCAL CONCLUÍDA COM SUCESSO!"
