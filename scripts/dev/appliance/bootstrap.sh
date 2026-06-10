#!/bin/bash
set -e

# Appliance Bootstrap Script
# Zero-touch installation foundation

echo "==========================================="
echo "   LLM Stack - Appliance Bootstrap"
echo "==========================================="

# 1. Environment Validation
echo "[1/4] Validating environment..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: This script must be run on Linux."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "Warning: Docker not found. Hardware acceleration might be limited."
fi

# 2. Generate Initial Config
echo "[2/4] Generating initial configuration..."
mkdir -p ./.appliance
if [ ! -f "./.appliance/config.yaml" ]; then
    cp ./config/appliance.defaults.yaml ./.appliance/config.yaml
    echo "Default configuration created at ./.appliance/config.yaml"
fi

# 3. Create Bootstrap Admin Token
echo "[3/4] Creating bootstrap admin token..."
BOOTSTRAP_TOKEN=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
# Do not print secret to stdout in real logs, but we save it securely
echo "ADMIN_TOKEN=$BOOTSTRAP_TOKEN" > ./.appliance/env.secret
chmod 600 ./.appliance/env.secret

# 4. Finalize
echo "[4/4] Finalizing bootstrap..."
echo "Bootstrap complete!"
echo "-------------------------------------------"
echo "Security Notice: Admin token saved to ./.appliance/env.secret"
echo "Please keep this file safe. It will expire based on config settings."
echo "==========================================="
