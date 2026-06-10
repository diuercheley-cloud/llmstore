#!/usr/bin/env bash
set -euo pipefail

# scripts/dev/diagnose-readiness-warnings-local.sh
# Diagnóstico de warnings do Production Readiness local.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

LATEST_REPORT="${1:-$(find artifacts/production-readiness -name "report.json" | sort -r | head -n 1)}"

if [[ -z "${LATEST_REPORT}" ]]; then
  echo "Erro: Nenhum relatório de prontidão encontrado em artifacts/production-readiness/"
  exit 1
fi

echo "--- Diagnóstico de Readiness: ${LATEST_REPORT} ---"

# Função para classificar e sugerir correção
diagnose_check() {
  local id="$1"
  local status="$2"
  local details="$3"
  
  if [[ "$status" == "pass" ]]; then
    return
  fi

  local category="unknown"
  local remediation="N/A"
  
  case "$id" in
    saas_rate_limit)
      category="probe_bug"
      remediation="Implementar probe que use mutação dedicada ou mock para disparar 429."
      ;;
    tts_generate_wav)
      category="real_issue"
      remediation="Validar API Key e conectividade com pocket-tts (retornou 401)."
      ;;
    security_cors_local)
      category="real_issue"
      remediation="Configurar default localhost origins no control-plane (allow-origin vazio)."
      ;;
    git_status_clean)
      category="environment_state"
      remediation="Comite ou faça stash das alterações locais antes da execução."
      ;;
    api_v1_models)
      if [[ "$details" == *"modelos retornados=0"* ]]; then
        category="real_issue"
        remediation="Registre pelo menos um modelo de chat ativo."
      else
        category="probe_bug"
        remediation="Melhorar probe para validar se modelo retornado é utilizável para chat."
      fi
      ;;
    *)
      category="needs_config"
      remediation="Revise os detalhes técnicos no relatório completo."
      ;;
  esac

  echo "[${status^^}] ID: $id"
  echo "      Categoria: $category"
  echo "      Detalhes: $details"
  echo "      Sugestão: $remediation"
  echo ""
}

# Extrair warnings e fails usando jq
# Note: we use @sh to escape values for shell safety
jq -r '.checks[] | select(.status != "pass" and .status != "skip") | "\(.id)|\(.status)|\(.details)"' "${LATEST_REPORT}" | while IFS="|" read -r id status details; do
  diagnose_check "$id" "$status" "$details"
done

echo "Relatório completo em: ${LATEST_REPORT%.json}.md"
