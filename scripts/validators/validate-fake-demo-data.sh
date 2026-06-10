#!/usr/bin/env bash
# Validador de dados ficticios para demo comercial
# Verifica que todos os dados sao seguros, marcados como DEMO, sem informacoes reais.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
FAKE_DIR="${ROOT_DIR}/demo-pack/fake-data"

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

check_json() {
  if python3 -m json.tool "$1" > /dev/null 2>&1; then
    pass "JSON valido: $1"
  else
    fail "JSON invalido: $1"
  fi
}

check_contains_demo() {
  if grep -qi "DEMO\|FICTICIO\|ficticio\|ficticio" "$1" 2>/dev/null; then
    pass "Contem marcador DEMO/FICTICIO: $1"
  else
    fail "SEM marcador DEMO/FICTICIO: $1"
  fi
}

check_no_real_cpf() {
  if grep -qP '\d{3}\.\d{3}\.\d{3}-\d{2}' "$1" 2>/dev/null; then
    local matches
    matches=$(grep -oP '\d{3}\.\d{3}\.\d{3}-\d{2}' "$1" 2>/dev/null || true)
    while IFS= read -r cpf; do
      if [[ "$cpf" =~ ^000\.000\.000-00$ || "$cpf" =~ ^123\.456\.789-00$ ]]; then
        pass "CPF ficticio permitido: ${cpf} em $1"
      else
        fail "Possivel CPF real: ${cpf} em $1"
      fi
    done <<< "$matches"
  else
    pass "Sem CPF: $1"
  fi
}

check_no_real_cnpj() {
  if grep -qP '\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}' "$1" 2>/dev/null; then
    local matches
    matches=$(grep -oP '\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}' "$1" 2>/dev/null || true)
    while IFS= read -r cnpj; do
      if [[ "$cnpj" =~ ^00\.000\.000/0001-00$ ]]; then
        pass "CNPJ ficticio permitido: ${cnpj} em $1"
      else
        fail "Possivel CNPJ real: ${cnpj} em $1"
      fi
    done <<< "$matches"
  else
    pass "Sem CNPJ: $1"
  fi
}

check_email_domain() {
  local fails=0
  while IFS= read -r line; do
    local domain
    domain=$(echo "$line" | sed -n 's/.*@\([^"]*\)".*/\1/p')
    if [[ -n "$domain" ]]; then
      if [[ "$domain" != "demo.local" && "$domain" != "example.local" ]]; then
        fail "Dominio de email nao autorizado: ${domain} em $1"
        fails=$((fails+1))
      fi
    fi
  done < <(grep -oP '[\w.+-]+@[\w-]+\.[\w.+-]+' "$1" 2>/dev/null || true)
  if [[ "$fails" -eq 0 ]]; then
    pass "Todos os emails usam dominios demo.local/example.local: $1"
  fi
}

check_no_real_phones() {
  local file="$1"
  local name="$2"
  local found=false
  while IFS= read -r phone; do
    phone_clean=$(echo "$phone" | tr -d '[+() -]')
    if [[ ${#phone_clean} -ge 13 ]]; then
      if ! echo "$phone" | grep -q "99999"; then
        fail "Possivel telefone real: ${phone} em ${name}"
        found=true
      fi
    fi
  done < <(grep -oP '\+55\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}' "$file" 2>/dev/null || true)
  if [[ "$found" == false ]]; then
    pass "Telefones usam prefixo 99999 (ficticio): ${name}"
  fi
}

check_no_secrets() {
  if grep -qP 'sk-[a-zA-Z0-9]{20,}' "$1" 2>/dev/null; then
    local matches
    matches=$(grep -oP 'sk-[a-zA-Z0-9]{20,}' "$1" 2>/dev/null || true)
    while IFS= read -r key; do
      if echo "$key" | grep -qi "demo\|example\|ficticio\|XXXXXXX"; then
        pass "Secret ficticio permitido: ${key:0:20}... em $1"
      else
        fail "Possivel secret real: ${key:0:20}... em $1"
      fi
    done <<< "$matches"
  else
    pass "Sem secrets: $1"
  fi
}

check_no_real_domains() {
  local file="$1"
  local name="$2"
  local suspicious_domains=("gmail.com" "yahoo.com" "hotmail.com" "outlook.com" "uol.com.br" "bol.com.br" "terra.com.br" "ig.com.br" "globo.com")
  for domain in "${suspicious_domains[@]}"; do
    if grep -qi "$domain" "$file" 2>/dev/null; then
      local ctx
      ctx=$(grep -i "$domain" "$file" 2>/dev/null | head -3)
      warn "Possivel dominio real: ${domain} em ${name} - contexto: ${ctx}"
    fi
  done
  pass "Sem dominios reais suspeitos: ${name}"
}

check_has_demo_true() {
  if grep -q '"demo":\s*true\|demo.*true\|"demo_marker":\s*true' "$1" 2>/dev/null; then
    pass "Contem demo=true: $1"
  else
    fail "SEM demo=true: $1"
  fi
}

echo ""
echo "=============================================="
echo "  VALIDACAO DE DADOS FICTICIOS - DEMO PACK"
echo "=============================================="
echo ""

echo "--- 1. Estrutura do diretorio fake-data ---"
if [[ -d "$FAKE_DIR" ]]; then
  pass "Diretorio fake-data/ existe"
else
  fail "Diretorio fake-data/ nao encontrado"
fi

if [[ -d "${FAKE_DIR}/rag_documents" ]]; then
  pass "Diretorio rag_documents/ existe"
else
  fail "Diretorio rag_documents/ nao encontrado"
fi

echo ""
echo "--- 2. Arquivos JSON existem e sao validos ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  if [[ -f "${FAKE_DIR}/${f}" ]]; then
    pass "Arquivo existe: ${f}"
    check_json "${FAKE_DIR}/${f}"
  else
    fail "Arquivo ausente: ${f}"
  fi
done

echo ""
echo "--- 3. Documentos RAG existem e contem marcador DEMO ---"
expected_docs=("politica_interna_horizonte.txt" "contrato_atlas.txt" "manual_suporte_orion.txt" "faq_prisma.txt" "base_conhecimento_nebula.txt")
for doc in "${expected_docs[@]}"; do
  if [[ -f "${FAKE_DIR}/rag_documents/${doc}" ]]; then
    pass "Documento RAG existe: ${doc}"
    check_contains_demo "${FAKE_DIR}/rag_documents/${doc}"
  else
    fail "Documento RAG ausente: ${doc}"
  fi
done

echo ""
echo "--- 4. Marcadores DEMO em todos os arquivos ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_contains_demo "${FAKE_DIR}/${f}"
done

echo ""
echo "--- 5. demo=true presente em todos os JSONs ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_has_demo_true "${FAKE_DIR}/${f}"
done

echo ""
echo "--- 6. Verificacao de CPFs e CNPJs ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_no_real_cpf "${FAKE_DIR}/${f}"
  check_no_real_cnpj "${FAKE_DIR}/${f}"
done

echo ""
echo "--- 7. Verificacao de e-mails (dominios autorizados) ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_email_domain "${FAKE_DIR}/${f}"
done

echo ""
echo "--- 8. Verificacao de telefones ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_no_real_phones "${FAKE_DIR}/${f}" "${f}"
done

echo ""
echo "--- 9. Verificacao de secrets ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_no_secrets "${FAKE_DIR}/${f}"
done

echo ""
echo "--- 10. Verificacao de dominios reais ---"
for f in clients.json plans.json invoices.json usage.json tts_samples.json prompts.json; do
  check_no_real_domains "${FAKE_DIR}/${f}" "${f}"
done

echo ""
echo "--- 11. Verificacao de documentos RAG ---"
for doc in "${expected_docs[@]}"; do
  check_no_real_cpf "${FAKE_DIR}/rag_documents/${doc}"
  check_no_real_cnpj "${FAKE_DIR}/rag_documents/${doc}"
  check_no_secrets "${FAKE_DIR}/rag_documents/${doc}"
done

echo ""
echo "--- 12. Nomes de clientes sao ficticios e marcados como Demo ---"
for client_name in "Clinica Horizonte Demo" "Juridico Atlas Demo" "Suporte Orion Demo" "Escola Prisma Demo" "Provedor API Nebula Demo"; do
  if grep -q "$client_name" "${FAKE_DIR}/clients.json" 2>/dev/null; then
    pass "Cliente encontrado: ${client_name}"
  else
    fail "Cliente ausente: ${client_name}"
  fi
done

echo ""
echo "=============================================="
echo "  RESUMO DA VALIDACAO"
echo "=============================================="
echo "  PASS: ${PASS}"
echo "  FAIL: ${FAIL}"
echo "  WARN: ${WARN}"
echo "=============================================="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo "Falhas encontradas. Revise os itens [FAIL] acima."
  exit 1
elif [[ "$WARN" -gt 0 ]]; then
  echo "Validacao concluida com avisos."
  exit 0
else
  echo "Dados ficticios validados com sucesso!"
  exit 0
fi
