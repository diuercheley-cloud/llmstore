#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
PASS=0
FAIL=0
WARN=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { WARN=$((WARN+1)); echo -e "  ${YELLOW}[WARN]${NC} $1"; }

echo ""
echo "=============================================="
echo "  DEMO PACK COMERCIAL - VALIDAÇÃO"
echo "=============================================="
echo ""

echo "--- 1. Estrutura demo-pack ---"
for f in \
    "demo-pack/README.md" \
    "demo-pack/demo-scenarios.json" \
    "demo-pack/demo-clients.json" \
    "demo-pack/demo-prompts.md" \
    "demo-pack/demo-api-requests.md" \
    "demo-pack/demo-objection-handling.md" \
    "demo-pack/demo-flow.md"; do
    if [[ -f "${ROOT_DIR}/${f}" ]]; then
        pass "Arquivo existe: ${f}"
    else
        fail "Arquivo ausente: ${f}"
    fi
done

echo ""
echo "--- 2. Documentos RAG demo ---"
for f in \
    "demo-pack/demo-documents/clinica_protocolos.txt" \
    "demo-pack/demo-documents/juridico_contratos.txt" \
    "demo-pack/demo-documents/suporte_knowledge_base.txt" \
    "demo-pack/demo-documents/educacao_material_didatico.txt" \
    "demo-pack/demo-documents/provedor_api_termos.txt"; do
    if [[ -f "${ROOT_DIR}/${f}" ]]; then
        pass "Documento RAG existe: ${f}"
    else
        fail "Documento RAG ausente: ${f}"
    fi
    if [[ -f "${ROOT_DIR}/${f}" ]] && ! grep -qi "demo" "${ROOT_DIR}/${f}" 2>/dev/null; then
        warn "${f} pode não conter marcação DEMO explícita"
    fi
done

echo ""
echo "--- 3. JSONs válidos ---"
for f in "demo-pack/demo-scenarios.json" "demo-pack/demo-clients.json"; do
    if python3 -m json.tool "${ROOT_DIR}/${f}" > /dev/null 2>&1; then
        pass "JSON válido: ${f}"
    else
        fail "JSON inválido: ${f}"
    fi
done

echo ""
echo "--- 4. Scripts seed/reset/validate ---"
for f in \
    "scripts/dev/seed-commercial-demo-pack.sh" \
    "scripts/dev/reset-commercial-demo-pack.sh" \
    "scripts/validators/validate-commercial-demo-pack.sh"; do
    if [[ -f "${ROOT_DIR}/${f}" ]]; then
        pass "Script existe: ${f}"
        if [[ -x "${ROOT_DIR}/${f}" ]]; then
            pass "Script executável: ${f}"
        else
            fail "Script não executável: ${f}"
        fi
    else
        fail "Script ausente: ${f}"
    fi
done

echo ""
echo "--- 5. Testes existem ---"
for f in \
    "tests/test_commercial_demo_pack.py" \
    "tests/test_commercial_demo_seed.py" \
    "tests/test_commercial_demo_security.py"; do
    if [[ -f "${ROOT_DIR}/${f}" ]]; then
        pass "Teste existe: ${f}"
    else
        fail "Teste ausente: ${f}"
    fi
done

echo ""
echo "--- 6.Segurança parcial (sem secrets em arquivos demo) ---"
secret_found=false
for pattern in "sk-[a-zA-Z0-9]" "ghp_" "-----BEGIN"; do
    if grep -rl "$pattern" "${ROOT_DIR}/demo-pack/" --include="*.md" --include="*.json" 2>/dev/null | grep -v "sk-demo-example\|sk-demo-xxxx" > /dev/null; then
        fail "Possível secret encontrado em demo-pack/"
        secret_found=true
    fi
done
if [[ "$secret_found" == false ]]; then
    pass "Nenhum secret real em demo-pack/"
fi

echo ""
echo "--- 7. Stack ativa (se ADMIN_TOKEN disponível) ---"
if [[ -n "${ADMIN_TOKEN}" ]]; then
    if curl -fsS "${BASE_URL}/health" > /dev/null 2>&1; then
        pass "Stack ativa em ${BASE_URL}"
    else
        fail "Stack não acessível em ${BASE_URL}"
    fi

    echo ""
    echo "--- 8. Dados demo na API (se stack ativa) ---"
    clients_json=$(curl -fsS "${BASE_URL}/admin/clients" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "[]")
    client_count=$(echo "$clients_json" | python3 -c "import json,sys; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")
    echo "  Total clientes cadastrados: ${client_count}"

    demo_clients=$(echo "$clients_json" | python3 -c "
import json,sys
data=json.load(sys.stdin)
demo=[c for c in data if c.get('metadata_json') and 'demo' in str(c.get('metadata_json',''))]
for c in demo:
    print(f\"  {c['name']} ({c['id']})\")
" 2>/dev/null || echo "  Nenhum cliente demo encontrado")
    if echo "$demo_clients" | grep -q "Clinica\|Juridico\|SuporteTech\|EducaMais\|APILayer"; then
        pass "Clientes demo encontrados na API"
    else
        warn "Clientes demo podem não estar carregados. Execute make demo-pack primeiro."
    fi

    echo ""
    echo "--- 9. Billing demo ---"
    invoices_json=$(curl -fsS "${BASE_URL}/admin/billing/invoices" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo '{"invoices":[]}')
    invoice_count=$(echo "$invoices_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('invoices', [])))" 2>/dev/null || echo "0")
    echo "  Total invoices: ${invoice_count}"
    if [[ "$invoice_count" -gt 0 ]]; then
        pass "Invoices encontradas (${invoice_count})"
    else
        warn "Nenhuma invoice encontrada"
    fi

    echo ""
    echo "--- 10. Demo summary ---"
    demo_summary=$(curl -fsS "${BASE_URL}/admin/demo/summary" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo '{"error":"unavailable"}')
    demo_enabled=$(echo "$demo_summary" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('demo_enabled', False))" 2>/dev/null || echo "false")
    if [[ "$demo_enabled" == "True" ]]; then
        pass "Demo mode ativo"
    else
        warn "Demo mode não está ativo (pode ser intencional)"
    fi
else
    warn "ADMIN_TOKEN não disponível, pulando validações de API"
fi

echo ""
echo "=============================================="
echo "  RESUMO"
echo "=============================================="
echo "  PASS: ${PASS}"
echo "  FAIL: ${FAIL}"
echo "  WARN: ${WARN}"
echo "=============================================="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo "❌ Falhas encontradas. Revise os itens [FAIL] acima."
    exit 1
elif [[ "$WARN" -gt 0 ]]; then
    echo "⚠️  Validação concluída com avisos."
    exit 0
else
    echo "✅ Demo pack comercial validado com sucesso!"
    exit 0
fi
