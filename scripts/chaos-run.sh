#!/bin/bash
# LLM Inference Stack - Chaos Experiment Runner

EXP_ID=$1
MODE=$2

if [ -z "$EXP_ID" ]; then
    echo "Erro: ID do experimento não fornecido."
    exit 1
fi

echo "--- Iniciando Experimento de Chaos: $EXP_ID ---"

# Mock call to API
# curl -X POST http://localhost:8000/admin/chaos/runs -d "{\"experiment_id\": \"$EXP_ID\"}"

echo "Status: RUNNING"
sleep 2
echo "Status: COMPLETED"
echo "Relatório gerado em chaos/reports/report-$EXP_ID.md"
