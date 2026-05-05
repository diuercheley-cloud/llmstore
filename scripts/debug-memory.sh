#!/bin/bash
# scripts/debug-memory.sh
# Script to monitor LLM memory usage across GPU and RAM to detect "leaks" or dual-loading.

set -e

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================================================================"
echo -e "LLM MEMORY DIAGNOSTIC (GPU & RAM)"
echo -e "================================================================================${NC}"

# 1. Check if nvidia-smi is available
HAS_GPU=false
if command -v nvidia-smi >/dev/null 2>&1; then
    HAS_GPU=true
    echo -e "${GREEN}[OK] GPU Hardware detected.${NC}"
else
    echo -e "${RED}[WARN] nvidia-smi not found. GPU monitoring will be skipped.${NC}"
fi

# 2. Identify running LLM containers
CONTAINERS=$(docker ps --filter "status=running" --format "{{.Names}}" | grep -E "data-plane|ollama" || true)

if [ -z "$CONTAINERS" ]; then
    echo -e "${RED}No running LLM data plane containers found.${NC}"
    exit 0
fi

echo -e "\n${YELLOW}--- Memory Usage by Container ---${NC}"
printf "%-25s | %-12s | %-12s | %-15s\n" "CONTAINER" "RAM (RSS)" "VRAM (GPU)" "MODEL"
printf "%-25s-|-%-12s-|-%-12s-|-%-15s\n" "-------------------------" "------------" "------------" "---------------"

for c in $CONTAINERS; do
    # Get RAM usage via docker stats (non-streaming)
    RAM=$(docker stats "$c" --no-stream --format "{{.MemUsage}}" | awk '{print $1}')
    
    # Get VRAM usage
    VRAM="N/A"
    if [ "$HAS_GPU" = true ]; then
        # Try to find the PID of the process inside the container that uses GPU
        CPID=$(docker inspect --format '{{.State.Pid}}' "$c")
        
        # Get used memory for all processes on GPU
        # We try to match by searching for the container's PID in the process tree of the host
        VRAM_TOTAL=0
        
        # Method 1: nvidia-smi pmon (most reliable for some drivers)
        PMON_VRAM=$(nvidia-smi pmon -c 1 | grep -E " $(pgrep -P $CPID | tr '\n' '|') " | awk '{sum+=$4} END {print sum}' || echo "0")
        
        # Method 2: nvidia-smi query-compute-apps
        QUERY_VRAM=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | while IFS=, read -r pid mem; do
            # Check if this pid is a child of our container pid
            if ps -p "$pid" -o ppid= 2>/dev/null | grep -q "$CPID" || [ "$pid" == "$CPID" ]; then
                echo "$mem"
            fi
        done | awk '{sum+=$1} END {print sum}' || echo "0")
        
        VRAM_TOTAL=$(( PMON_VRAM > QUERY_VRAM ? PMON_VRAM : QUERY_VRAM ))
        
        if [ "$VRAM_TOTAL" -gt 0 ]; then
            VRAM="${VRAM_TOTAL}MiB"
        else
            VRAM="Check Global"
        fi
    fi

    # Get Model Name
    MODEL="Unknown"
    if [[ "$c" == *"ollama"* ]]; then
        MODEL=$(docker exec "$c" ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | head -n 1)
    else
        MODEL=$(docker exec "$c" env 2>/dev/null | grep MODEL_FILE | cut -d'=' -f2 | xargs basename 2>/dev/null || echo "Unknown")
    fi

    printf "%-25s | %-12s | %-12s | %-15s\n" "$c" "$RAM" "$VRAM" "$MODEL"
done

echo -e "\n${YELLOW}* Note: MiB* indicates a guessed value based on process name matching.${NC}"

# 3. Check for potential "Leaks" (High RAM + High VRAM)
echo -e "\n${YELLOW}--- Analysis ---${NC}"
for c in $CONTAINERS; do
    RAM_BYTES=$(docker stats "$c" --no-stream --format "{{.MemUsage}}" | awk '{print $1}' | sed 's/GiB/*1024/g;s/MiB//g;s/KiB/\/1024/g' | bc -l 2>/dev/null || echo "0")
    # If RAM > 2GB and we expect it to be on GPU, warn
    if (( $(echo "$RAM_BYTES > 2048" | bc -l) )); then
        echo -e "${RED}[WARN] Container $c is using high RAM ($(docker stats "$c" --no-stream --format "{{.MemUsage}}" | awk '{print $1}')).${NC}"
        echo -e "       This might indicate that the model is NOT fully offloaded to GPU."
    else
        echo -e "${GREEN}[OK] Container $c RAM usage looks reasonable for control overhead.${NC}"
    fi
done

echo -e "\n${YELLOW}--- GPU Processes (nvidia-smi) ---${NC}"
if [ "$HAS_GPU" = true ]; then
    nvidia-smi
else
    echo "N/A"
fi

echo -e "\n${YELLOW}================================================================================${NC}"
