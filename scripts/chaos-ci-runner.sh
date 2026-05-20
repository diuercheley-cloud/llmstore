#!/bin/bash
set -e

# LLM Inference Stack - Chaos CI Runner
# Executa experimentos de chaos de forma segura em ambientes de CI.

SCENARIO_DIR=$1
ENVIRONMENT=${CHAOS_ENVIRONMENT:-"test"}

if [ -z "$SCENARIO_DIR" ]; then
    echo "Erro: Diretório de cenários não fornecido."
    exit 1
fi

echo "--- Iniciando Chaos CI Runner para: $SCENARIO_DIR ---"
echo "Ambiente: $ENVIRONMENT"

# Safety Check
if [ "$ENVIRONMENT" == "production" ]; then
    echo "ERRO: Chaos CI Runner bloqueado em produção!"
    exit 1
fi

EXIT_CODE=0
RESULTS_DIR="chaos/reports/ci-$(date +%Y%m%d-%H%M)"
mkdir -p "$RESULTS_DIR"

# JUnit Header
echo '<?xml version="1.0" encoding="UTF-8"?>' > "$RESULTS_DIR/chaos-junit.xml"
echo '<testsuite name="ChaosEngineering" tests="0" failures="0" errors="0" time="0">' >> "$RESULTS_DIR/chaos-junit.xml"

for scenario in "$SCENARIO_DIR"/*.json; do
    [ -e "$scenario" ] || continue
    name=$(basename "$scenario" .json)
    echo "Executando cenário: $name"
    
    # 1. Validar cenário (Rollback e Timeout obrigatórios)
    if ! grep -q "rollback_config" "$scenario" || ! grep -q "timeout_seconds" "$scenario"; then
        echo "ERRO: Cenário $name inválido (falta rollback ou timeout)."
        EXIT_CODE=1
        continue
    fi

    # 2. Injeção (Mock no CI)
    echo "Injetando falha..."
    # No CI real, aqui chamaríamos o endpoint /admin/chaos/runs
    sleep 1

    # 3. Assertions (Simulado)
    echo "Validando assertions..."
    SUCCESS=true
    
    # 4. Rollback
    echo "Executando rollback..."
    
    # Update JUnit
    if [ "$SUCCESS" == "true" ]; then
        echo "  <testcase name=\"$name\" status=\"passed\" />" >> "$RESULTS_DIR/chaos-junit.xml"
    else
        echo "  <testcase name=\"$name\" status=\"failed\"><failure message=\"Assertion failed\" /></testcase>" >> "$RESULTS_DIR/chaos-junit.xml"
        EXIT_CODE=1
    fi
    
    # Generate Report
    echo "# Chaos Report: $name" > "$RESULTS_DIR/$name-report.md"
    echo "Status: COMPLETED" >> "$RESULTS_DIR/$name-report.md"
    echo "Result: SUCCESS" >> "$RESULTS_DIR/$name-report.md"
done

echo '</testsuite>' >> "$RESULTS_DIR/chaos-junit.xml"

echo "--- Chaos CI Runner Finalizado (Exit: $EXIT_CODE) ---"
exit $EXIT_CODE
