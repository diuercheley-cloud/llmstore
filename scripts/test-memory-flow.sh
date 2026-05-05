#!/bin/bash
# scripts/test-memory-flow.sh
# Test script to verify memory release and allocation when toggling models.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODEL="gemma"

echo -e "${YELLOW}Starting Memory Leak Test for Model: $MODEL${NC}"

# 1. Baseline
echo -e "\n${YELLOW}--- PHASE 1: Baseline ---${NC}"
./scripts/debug-memory.sh

# 2. Deactivate
echo -e "\n${YELLOW}--- PHASE 2: Deactivating Model $MODEL ---${NC}"
./scripts/deactivate-model.sh "$MODEL"

echo "Waiting for 5 seconds for memory to clear..."
sleep 5

./scripts/debug-memory.sh

# 3. Check if VRAM cleared
if command -v nvidia-smi >/dev/null 2>&1; then
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    echo -e "${GREEN}Current VRAM usage: ${VRAM_USED}MiB${NC}"
fi

# 4. Reactivate
echo -e "\n${YELLOW}--- PHASE 3: Reactivating Model $MODEL ---${NC}"
./scripts/activate-model.sh "$MODEL"

echo "Waiting for 10 seconds for model to load..."
sleep 10

./scripts/debug-memory.sh

echo -e "\n${GREEN}Test Complete.${NC}"
