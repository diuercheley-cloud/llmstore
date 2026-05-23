#!/bin/bash
set -e

# LLM Inference Stack - SOC 2 Access Review
# Consolida a lista de usuários e permissões para revisão trimestral.

echo "--- Gerando Relatório de Revisão de Acesso ---"

# 1. Extrair usuários (Simulado)
echo "Usuários do Painel Admin:" > artifacts/compliance/latest/access-review-data.txt
# No banco real: psql -c "SELECT username, role FROM users;" >> access-review-data.txt
echo "admin - SuperUser" >> artifacts/compliance/latest/access-review-data.txt
echo "operator-01 - Operator" >> artifacts/compliance/latest/access-review-data.txt
echo "auditor-01 - Auditor" >> artifacts/compliance/latest/access-review-data.txt

# 2. Extrair chaves de API (Simulado)
echo "API Keys Ativas:" >> artifacts/compliance/latest/access-review-data.txt
echo "PROD-CLIENT-A: Active" >> artifacts/compliance/latest/access-review-data.txt

echo "Dados consolidados em artifacts/compliance/latest/access-review-data.txt"
echo "Acesse /admin/compliance/soc2/access-review para registrar a revisão."
