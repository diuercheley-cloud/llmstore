#!/bin/bash
# scripts/list-gpu-models.sh

set -e

echo "================================================================================"
echo "LLM GPU MONITORING"
echo "================================================================================"

# 1. GPU Hardware Status
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "GPU Status:"
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader | while IFS=, read -r idx name total used util; do
        echo "  [$idx] $name: $used / $total (Usage: $util)"
    done
else
    echo "GPU Status: nvidia-smi not found"
fi

echo "--------------------------------------------------------------------------------"
echo "Running LLM Services (Docker):"
echo "--------------------------------------------------------------------------------"

# Find containers that are likely serving models
# We look for containers with "data-plane" in the name or "ollama"
CONTAINERS=$(docker ps --filter "status=running" --format "{{.Names}}" | grep -E "data-plane|ollama" || true)

if [ -z "$CONTAINERS" ]; then
    echo "  No running LLM data plane containers found."
else
    printf "  %-35s | %-35s | %-6s\n" "CONTAINER" "MODEL" "PORT"
    printf "  %-35s-|-%-35s-|-%-6s\n" "-----------------------------------" "-----------------------------------" "------"
    
    for c in $CONTAINERS; do
        if [[ "$c" == *"ollama"* ]]; then
            # For Ollama, we might need to query its API to see loaded models
            MODELS=$(docker exec "$c" ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | tr '\n' ',' | sed 's/,$//')
            printf "  %-35s | %-35s | %-6s\n" "$c" "${MODELS:-Ollama (no models loaded)}" "11434"
        else
            # For our standard data-plane (llama.cpp based)
            MODEL=$(docker exec "$c" env 2>/dev/null | grep MODEL_FILE | cut -d'=' -f2)
            PORT=$(docker exec "$c" env 2>/dev/null | grep LLAMA_SERVER_PORT | cut -d'=' -f2)
            
            # If MODEL_FILE is empty, try to get it from logs or cmd
            if [ -z "$MODEL" ]; then
                MODEL=$(docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep MODEL_FILE | cut -d'=' -f2)
            fi
            
            printf "  %-35s | %-35s | %-6s\n" "$c" "${MODEL:-Unknown}" "${PORT:-N/A}"
        fi
    done
fi

echo "--------------------------------------------------------------------------------"
echo "Active Processes (Host):"
echo "--------------------------------------------------------------------------------"

# Try to find any local processes that might be using the GPU (if not in docker)
# This is a bit speculative but helps if the user is running things locally
if command -v nvidia-smi >/dev/null 2>&1; then
    PIDS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null || true)
    if [ ! -z "$PIDS" ] && [ "$PIDS" != "No running processes found" ]; then
        for pid in $PIDS; do
            PROC_NAME=$(ps -p "$pid" -o comm= 2>/dev/null || echo "Unknown")
            MEM=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits --id="$pid" 2>/dev/null || echo "?")
            echo "  PID: $pid | Name: $PROC_NAME | GPU Mem: ${MEM}MiB"
        done
    else
        echo "  No specific GPU processes identified by nvidia-smi."
    fi
fi

echo "================================================================================"
