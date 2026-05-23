#!/bin/bash
set -e

# LLM Inference Stack - Compliance Release Gate
# Bloqueia a release se houverem gaps críticos sem exceção.

TAG=$1
echo "--- Validando Compliance Gate para Release $TAG ---"

# 1. Checar por Gaps Críticos (Simulação)
# Em um cenário real, consultaríamos o banco ou arquivos de auditoria.
if [ -f "artifacts/compliance/latest/gap-analysis.md" ]; then
    if grep -q "CRITICAL" artifacts/compliance/latest/gap-analysis.md; then
        echo "ERRO: Gaps críticos detectados no relatório de prontidão."
        # Verifica se existe exceção aprovada (simulado)
        if ! [ -f "compliance/exceptions/approved_exceptions.yaml" ]; then
            echo "Bloqueando release: Gaps críticos sem exceção aprovada."
            exit 1
        fi
    fi
fi

# 2. Artifact Sanitization Scan
echo "Escaneando artefatos de release por segredos e prompts..."
# scripts/verify-release-artifacts.sh já faz parte da verificação básica
bash scripts/verify-release-artifacts.sh "$TAG"

echo "--- Compliance Release Gate: APPROVED ---"
