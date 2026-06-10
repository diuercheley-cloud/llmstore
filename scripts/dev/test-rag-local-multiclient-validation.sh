#!/usr/bin/env bash
set -euo pipefail

echo "Rodando test-rag-local-multiclient-validation.sh..."
OUTPUT=$(./scripts/validators/validate-rag-local-multiclient.sh 2>&1)

echo "$OUTPUT"

REQUIRED_STRINGS=(
  "OK: Cliente B não vê documentos do Cliente A"
  "OK: RAG respondeu corretamente para Cliente A"
  "OK: Cliente B recebeu 404 ao tentar acessar documento do Cliente A"
  "OK: limite de documentos do plano Free bloqueou upload excedente"
  "OK: Documento removido com sucesso"
  "--- VALIDAÇÃO RAG CONCLUÍDA COM SUCESSO ---"
)

for str in "${REQUIRED_STRINGS[@]}"; do
  if echo "$OUTPUT" | grep -F -q -e "$str"; then
    echo "Encontrado: $str"
  else
    echo "FALHA: String obrigatória não encontrada: $str"
    exit 1
  fi
done

echo "TESTE DE VALIDAÇÃO PASSOU COM SUCESSO."
