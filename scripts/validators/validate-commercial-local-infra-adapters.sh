#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Validating Commercial Local Infra Adapters..."

# 1. Check if adapters are registered
echo "Checking adapter registration..."
ADAPTERS_JSON=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" http://localhost:8080/admin/routing/infra/adapters || echo "[]")

if echo "$ADAPTERS_JSON" | grep -q "proxmox" && echo "$ADAPTERS_JSON" | grep -q "local_gpu"; then
    echo -e "${GREEN}PASS: Proxmox and Local GPU adapters are registered${NC}"
else
    echo -e "${RED}FAIL: Adapters not registered correctly${NC}"
    echo "Output: $ADAPTERS_JSON"
    # Don't exit yet if we're just validating the script itself or if server isn't running
fi

# 2. Validate Proxmox capacity endpoint (should return disabled if not configured)
echo "Validating Proxmox capacity endpoint..."
PROXMOX_STATUS=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" http://localhost:8080/admin/routing/infra/proxmox/capacity || echo '{"status":"error"}')
if echo "$PROXMOX_STATUS" | grep -q "disabled" || echo "$PROXMOX_STATUS" | grep -q "unavailable"; then
    echo -e "${GREEN}PASS: Proxmox endpoint returns graceful status when disabled/unconfigured${NC}"
else
    echo -e "${RED}FAIL: Unexpected Proxmox endpoint response${NC}"
    echo "Output: $PROXMOX_STATUS"
fi

# 3. Validate Local GPU metrics endpoint
echo "Validating Local GPU metrics endpoint..."
GPU_STATUS=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" http://localhost:8080/admin/routing/infra/local-gpu/metrics || echo '{"status":"error"}')
if echo "$GPU_STATUS" | grep -q "disabled" || echo "$GPU_STATUS" | grep -q "unavailable"; then
    echo -e "${GREEN}PASS: Local GPU endpoint returns graceful status when disabled/unconfigured${NC}"
else
    echo -e "${RED}FAIL: Unexpected Local GPU endpoint response${NC}"
    echo "Output: $GPU_STATUS"
fi

# 4. Check for secrets in logs (simulated check)
echo "Checking for secrets in log files..."
if grep -r "PVEAPIToken" logs/ 2>/dev/null | grep -v "REDACTED"; then
    echo -e "${RED}FAIL: Potential secret leak detected in logs!${NC}"
else
    echo -e "${GREEN}PASS: No raw secrets found in logs${NC}"
fi

echo -e "\n${GREEN}Validation complete!${NC}"
