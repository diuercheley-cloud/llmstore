#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

DRY_RUN=true
CONFIRMED=false
INCLUDE_RAG=false
INCLUDE_TTS=false
INCLUDE_INVOICES=false
INCLUDE_USAGE=false
DEMO_PREFIX="demo-"
SHOW_HELP=false

PROTECTED_PATTERNS=(
  "^models/"
  "^backups/"
  "^releases/"
  "^\.env\.local"
  "^\.local/"
  "^artifacts/"
  "^exports/"
)

declare -a DELETED_CLIENTS=()
declare -a DELETED_KEYS=()
declare -a DELETED_RAG=()
declare -a DELETED_TTS=()
declare -a DELETED_INVOICES=()
declare -a DELETED_USAGE=()
declare -a DELETED_PLANS=()
declare -a DELETED_FILES=()
declare -a SAFETY_SKIPS=()
declare -a ERRORS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
  cat <<EOF
Uso: $(basename "$0") [opcoes]

Reseta dados do Demo Pack Comercial com seguranca.

MODO PADRAO: --dry-run (apenas simula, nao apaga nada).

Opcoes:
  --dry-run            Modo simulacao (padrao). Nenhum dado e alterado.
  --yes                Confirma e executa o reset real.
  --include-rag        Remove tambem documentos RAG demo.
  --include-tts        Remove tambem arquivos TTS demo.
  --include-invoices   Remove tambem faturas demo.
  --include-usage      Remove tambem registros de uso demo.
  --demo-prefix        Prefixo para identificar planos/keys demo (padrao: demo-).
  --help               Mostra esta mensagem e sai.

SEGURANCA:
  - Nunca apaga clientes sem metadata demo=true.
  - Nunca apaga models/, backups/, releases/, .env.local, exports/.
  - Exige --yes para execucao real.
  - Gera relatorio em artifacts/demo-reset/<timestamp>/.
EOF
  exit 0
}

log()   { echo -e "  ${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "  ${RED}[ERROR]${NC} $1"; ERRORS+=("$1"); }
dry()   { echo -e "  ${CYAN}[DRY-RUN]${NC} $1"; }
action(){ echo -e "  ${GREEN}[ACTION]${NC} $1"; }

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=true; shift ;;
      --yes) DRY_RUN=false; CONFIRMED=true; shift ;;
      --include-rag) INCLUDE_RAG=true; shift ;;
      --include-tts) INCLUDE_TTS=true; shift ;;
      --include-invoices) INCLUDE_INVOICES=true; shift ;;
      --include-usage) INCLUDE_USAGE=true; shift ;;
      --demo-prefix) DEMO_PREFIX="$2"; shift 2 ;;
      --help|-h) SHOW_HELP=true; shift ;;
      *) error "Opcao desconhecida: $1"; usage ;;
    esac
  done
}

check_safety() {
  local target="$1"
  for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$target" =~ $pattern ]]; then
      SAFETY_SKIPS+=("$target (protegido por: $pattern)")
      return 1
    fi
  done
  return 0
}

fetch_clients_json() {
  if [[ -z "${ADMIN_TOKEN}" ]]; then
    echo '{"error":"no_token"}'
    return
  fi
  curl -fsS "${BASE_URL}/admin/clients" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "[]"
}

fetch_plans_json() {
  if [[ -z "${ADMIN_TOKEN}" ]]; then
    echo '{"error":"no_token"}'
    return
  fi
  curl -fsS "${BASE_URL}/admin/billing/plans" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "[]"
}

filter_demo_clients() {
  python3 -c "
import json, sys
try:
    clients = json.load(sys.stdin)
except Exception:
    print('[]')
    sys.exit(0)
if not isinstance(clients, list):
    print('[]')
    sys.exit(0)
demo_clients = []
for c in clients:
    meta = c.get('metadata_json') or '{}'
    try:
        md = json.loads(meta) if isinstance(meta, str) else meta
    except json.JSONDecodeError:
        md = {}
    is_demo = str(md.get('demo', '')).lower() in ('true', '1', 'yes')
    if is_demo:
        demo_clients.append(c)
    elif c.get('name', '').lower().endswith('demo'):
        demo_clients.append(c)
print(json.dumps(demo_clients))
"
}

filter_demo_plans() {
  local prefix="${DEMO_PREFIX}"
  python3 -c "
import json, sys
prefix = '${prefix}'
try:
    plans = json.load(sys.stdin)
except Exception:
    print('[]')
    sys.exit(0)
if not isinstance(plans, list):
    print('[]')
    sys.exit(0)
demo_plans = [p for p in plans if p.get('code', '').startswith(prefix)]
print(json.dumps(demo_plans))
"
}

delete_client_data() {
  local client_id="$1"
  local client_name="$2"

  if [[ "$DRY_RUN" == true ]]; then
    dry "Removeria dados do cliente: ${client_name} (${client_id})"
    return
  fi

  action "Removendo dados do cliente: ${client_name} (${client_id})"

  if [[ "$INCLUDE_USAGE" == true ]]; then
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM usage_records WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM quota_counters WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM rag_usage_events WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    DELETED_USAGE+=("${client_name} (${client_id})")
  fi

  if [[ "$INCLUDE_RAG" == true ]]; then
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM rag_document_chunks WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM rag_documents WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    DELETED_RAG+=("${client_name} (${client_id})")
  fi

  if [[ "$INCLUDE_TTS" == true ]]; then
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM tts_generation_jobs WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    DELETED_TTS+=("${client_name} (${client_id})")
  fi

  if [[ "$INCLUDE_INVOICES" == true ]]; then
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM customer_payments WHERE invoice_id IN (SELECT id FROM billing_invoices WHERE client_id = '${client_id}');" > /dev/null 2>&1 || true
    dc exec -T postgres psql -U llm_gateway -d llm_gateway \
      -c "DELETE FROM billing_invoices WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
    DELETED_INVOICES+=("${client_name} (${client_id})")
  fi

  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM generation_jobs WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM security_events WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM request_logs WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM api_keys WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM client_feature_blocks WHERE client_id = '${client_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM clients WHERE id = '${client_id}';" > /dev/null 2>&1 || true
  DELETED_CLIENTS+=("${client_name} (${client_id})")
}

delete_demo_plan() {
  local plan_id="$1"
  local plan_code="$2"

  if [[ "$DRY_RUN" == true ]]; then
    dry "Removeria plano demo: ${plan_code} (${plan_id})"
    return
  fi

  action "Removendo plano demo: ${plan_code} (${plan_id})"
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM pricing_rules WHERE billing_plan_id = '${plan_id}';" > /dev/null 2>&1 || true
  dc exec -T postgres psql -U llm_gateway -d llm_gateway \
    -c "DELETE FROM billing_plans WHERE id = '${plan_id}';" > /dev/null 2>&1 || true
  DELETED_PLANS+=("${plan_code} (${plan_id})")
}

delete_credentials_file() {
  local creds_file="${ROOT_DIR}/.local/demo-commercial-clients.env"

  if ! check_safety "$creds_file"; then
    warn "Arquivo de credenciais protegido, pulando: ${creds_file}"
    return
  fi

  if [[ ! -f "$creds_file" ]]; then
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry "Removeria arquivo de credenciais: ${creds_file}"
    return
  fi

  action "Removendo arquivo de credenciais: ${creds_file}"
  rm -f "$creds_file"
  DELETED_FILES+=("${creds_file}")
}

generate_report() {
  local timestamp
  timestamp=$(date +%Y%m%d_%H%M%S)
  local report_dir="${ROOT_DIR}/artifacts/demo-reset/${timestamp}"
  mkdir -p "$report_dir"

  local status
  if [[ ${#ERRORS[@]} -gt 0 ]]; then
    status="ERRORS"
  elif [[ "$DRY_RUN" == true ]]; then
    status="DRY_RUN"
  else
    status="COMPLETED"
  fi

  local json_report="${report_dir}/reset-report.json"
  local md_report="${report_dir}/reset-report.md"

  cat > "$json_report" <<JSONEOF
{
  "timestamp": "$(date -Iseconds)",
  "status": "${status}",
  "dry_run": ${DRY_RUN},
  "options": {
    "include_rag": ${INCLUDE_RAG},
    "include_tts": ${INCLUDE_TTS},
    "include_invoices": ${INCLUDE_INVOICES},
    "include_usage": ${INCLUDE_USAGE},
    "demo_prefix": "${DEMO_PREFIX}"
  },
  "summary": {
    "clients_removed": ${#DELETED_CLIENTS[@]},
    "plans_removed": ${#DELETED_PLANS[@]},
    "api_keys_removed": ${#DELETED_KEYS[@]},
    "rag_docs_removed": ${#DELETED_RAG[@]},
    "tts_files_removed": ${#DELETED_TTS[@]},
    "invoices_removed": ${#DELETED_INVOICES[@]},
    "usage_records_removed": ${#DELETED_USAGE[@]},
    "files_removed": ${#DELETED_FILES[@]},
    "safety_skips": ${#SAFETY_SKIPS[@]},
    "errors": ${#ERRORS[@]}
  },
  "clients_removed": $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${DELETED_CLIENTS[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]')))"),
  "plans_removed": $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${DELETED_PLANS[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]')))"),
  "safety_skips": $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${SAFETY_SKIPS[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]')))"),
  "errors": $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${ERRORS[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]')))")
}
JSONEOF

  cat > "$md_report" <<MDEOF
# Relatorio de Reset - Demo Pack Comercial

**Data:** $(date)
**Status:** ${status}
**Dry Run:** ${DRY_RUN}

## Opcoes
- Include RAG: ${INCLUDE_RAG}
- Include TTS: ${INCLUDE_TTS}
- Include Invoices: ${INCLUDE_INVOICES}
- Include Usage: ${INCLUDE_USAGE}
- Demo Prefix: ${DEMO_PREFIX}

## Resumo

| Item | Quantidade |
|------|-----------|
| Clientes removidos | ${#DELETED_CLIENTS[@]} |
| Planos removidos | ${#DELETED_PLANS[@]} |
| API Keys removidas | ${#DELETED_KEYS[@]} |
| Documentos RAG removidos | ${#DELETED_RAG[@]} |
| Arquivos TTS removidos | ${#DELETED_TTS[@]} |
| Faturas removidas | ${#DELETED_INVOICES[@]} |
| Registros de uso removidos | ${#DELETED_USAGE[@]} |
| Arquivos removidos | ${#DELETED_FILES[@]} |
| Safety Skips | ${#SAFETY_SKIPS[@]} |
| Erros | ${#ERRORS[@]} |

## Clientes Removidos
MDEOF

  for c in "${DELETED_CLIENTS[@]}"; do
    echo "- ${c}" >> "$md_report"
  done

  echo -e "\n## Planos Removidos" >> "$md_report"
  for p in "${DELETED_PLANS[@]}"; do
    echo "- ${p}" >> "$md_report"
  done

  if [[ ${#SAFETY_SKIPS[@]} -gt 0 ]]; then
    echo -e "\n## Safety Skips (dados preservados)" >> "$md_report"
    for s in "${SAFETY_SKIPS[@]}"; do
      echo "- ${s}" >> "$md_report"
    done
  fi

  if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo -e "\n## Erros" >> "$md_report"
    for e in "${ERRORS[@]}"; do
      echo "- ${e}" >> "$md_report"
    done
  fi

  echo -e "\n---\n*Relatorio gerado automaticamente por reset-commercial-demo-pack.sh*" >> "$md_report"

  log "Relatorio salvo em: ${report_dir}/"
  log "  JSON: ${json_report}"
  log "  MD:   ${md_report}"
}

print_security_guarantees() {
  echo ""
  echo "=============================================="
  echo "  GARANTIAS DE SEGURANCA"
  echo "=============================================="
  echo "  ✓ NUNCA apaga clientes sem metadata demo=true"
  echo "  ✓ NUNCA apaga models/"
  echo "  ✓ NUNCA apaga backups/"
  echo "  ✓ NUNCA apaga releases/"
  echo "  ✓ NUNCA apaga .env.local"
  echo "  ✓ NUNCA apaga exports/"
  echo "  ✓ NUNCA apaga dados nao-demo"
  echo "  ✓ --dry-run e o padrao (modo seguro)"
  echo "  ✓ --yes obrigatorio para execucao real"
  echo "  ✓ Relatorio gerado em artifacts/demo-reset/"
  echo "=============================================="
  echo ""
}

main() {
  parse_args "$@"

  if [[ "$SHOW_HELP" == true ]]; then
    usage
  fi

  echo ""
  echo "=============================================="
  echo "  RESET - DEMO PACK COMERCIAL"
  echo "=============================================="
  echo ""

  print_security_guarantees

  if [[ -z "${ADMIN_TOKEN}" ]]; then
    error "ADMIN_TOKEN nao definido. Configure no .env ou exporte a variavel."
    if [[ "$DRY_RUN" == false ]]; then
      exit 1
    fi
  fi

  if [[ "$DRY_RUN" == true ]]; then
    warn "MODO DRY-RUN: Nenhum dado sera alterado."
    echo ""
  else
    if [[ "$CONFIRMED" != true ]]; then
      error "Modo --dry-run desativado mas --yes nao foi fornecido."
      error "Use --yes para confirmar o reset real."
      error "Use --dry-run (padrao) para simulacao segura."
      exit 1
    fi
    warn "MODO REAL: Dados demo serao removidos!"
    echo ""
  fi

  local raw_clients
  raw_clients=$(fetch_clients_json)
  if [[ "$raw_clients" == '{"error":"no_token"}' ]]; then
    error "ADMIN_TOKEN nao definido. Impossivel buscar clientes."
    if [[ "$DRY_RUN" == false ]]; then
      exit 1
    fi
  fi
  local clients_json
  clients_json=$(echo "$raw_clients" | filter_demo_clients)
  local demo_clients
  demo_clients=$(echo "$clients_json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for c in data:
            print(f\"{c['id']}|{c['name']}\")
except Exception:
    pass
" 2>/dev/null || true)

  local raw_plans
  raw_plans=$(fetch_plans_json)
  local plans_json
  plans_json=$(echo "$raw_plans" | filter_demo_plans)
  local demo_plans
  demo_plans=$(echo "$plans_json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for p in data:
            print(f\"{p['id']}|{p['code']}\")
except Exception:
    pass
" 2>/dev/null || true)

  echo "--- Removendo clientes demo ---"
  if [[ -z "$demo_clients" ]]; then
    log "Nenhum cliente demo encontrado."
  else
    while IFS='|' read -r cid cname; do
      [[ -z "$cid" ]] && continue
      echo ""
      delete_client_data "$cid" "$cname"
    done <<< "$demo_clients"
  fi

  echo ""
  echo "--- Removendo planos demo ---"
  if [[ -z "$demo_plans" ]]; then
    log "Nenhum plano demo encontrado."
  else
    while IFS='|' read -r pid pcode; do
      [[ -z "$pid" ]] && continue
      echo ""
      delete_demo_plan "$pid" "$pcode"
    done <<< "$demo_plans"
  fi

  echo ""
  echo "--- Removendo credenciais locais ---"
  delete_credentials_file

  echo ""
  echo "--- Gerando relatorio ---"
  generate_report

  echo ""
  echo "=============================================="
  if [[ "$DRY_RUN" == true ]]; then
    echo "  DRY-RUN CONCLUIDO - Nenhum dado alterado."
  else
    echo "  RESET CONCLUIDO"
    echo "  Para recriar: make demo-pack"
  fi
  echo "=============================================="

  if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "  Erros encontrados:"
    for e in "${ERRORS[@]}"; do
      echo "    - ${e}"
    done
    exit 1
  fi

  print_security_guarantees
}

main "$@"
