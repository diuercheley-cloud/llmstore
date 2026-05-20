#!/bin/bash
set -e

# LLM Inference Stack - Compliance Checker
# Valida a integridade dos arquivos de governança e políticas.

echo "--- Iniciando Auditoria de Compliance Readiness ---"

# 1. Validar Políticas (Lint)
echo "Validando Políticas em compliance/policies/..."
for f in compliance/policies/*.md; do
    if ! grep -Fq "**Owner**" "$f"; then
        echo "ERRO: Política $f não possui um Owner definido."
        exit 1
    fi
    if ! grep -Fq "**Review Frequency**" "$f"; then
        echo "ERRO: Política $f não possui frequência de revisão."
        exit 1
    fi
done

# 2. Validar Risk Register
echo "Validando Risk Register..."
if [ -f "compliance/risk/risk-register.yaml" ]; then
    # Checa se todos os riscos possuem treatment_plan (simples grep)
    if grep -q "treatment_plan: \"\"" compliance/risk/risk-register.yaml; then
        echo "ERRO: Existem riscos sem plano de tratamento definido."
        exit 1
    fi
fi

# 3. Validar Control Map
echo "Validando Control Map..."
if [ -f "compliance/mappings/soc2_iso27001_control_map.yaml" ]; then
    if grep -q "owner_role: \"\"" compliance/mappings/soc2_iso27001_control_map.yaml; then
        echo "ERRO: Existem controles sem dono definido."
        exit 1
    fi
fi

echo "--- Auditoria de Compliance: PASS ---"
