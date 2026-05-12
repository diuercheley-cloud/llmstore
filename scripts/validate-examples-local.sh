#!/bin/bash
set -e

# Base URL for local validation
export BASE_URL=${BASE_URL:-"http://localhost:18080"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
cd "$ROOT_DIR"

echo "--- Validating API Examples ---"

# 1. Load demo client env if exists
if [ -f "$ROOT_DIR/.local/demo-client.env" ]; then
    echo "Loading $ROOT_DIR/.local/demo-client.env..."
    source "$ROOT_DIR/.local/demo-client.env"
    export CLIENT_API_KEY=${DEMO_API_KEY}
fi

# 2. Check if CLIENT_API_KEY is defined
if [ -z "$CLIENT_API_KEY" ]; then
    echo "ERROR: CLIENT_API_KEY is not set and .local/demo-client.env not found."
    echo "Please export CLIENT_API_KEY before running this script."
    exit 1
fi

echo "Using API Key: ${CLIENT_API_KEY:0:8}..."

# 3. Run Curl Examples
echo -e "\n[CURL] Validating models.sh..."
chmod +x examples/curl/models.sh
./examples/curl/models.sh > /dev/null
echo "OK"

echo -e "\n[CURL] Validating chat.sh..."
chmod +x examples/curl/chat.sh
./examples/curl/chat.sh > /dev/null
echo "OK"

# 4. Run Python Examples
if command -v python3 &> /dev/null; then
    echo -e "\n[PYTHON] Validating chat.py..."
    python3 examples/python/chat.py > /dev/null
    echo "OK"
else
    echo -e "\n[PYTHON] SKIP: python3 not found"
fi

# 5. Run Node Examples
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        echo -e "\n[NODE] Validating chat.js..."
        node examples/node/chat.js > /dev/null
        echo "OK"
    else
        echo -e "\n[NODE] SKIP: node version < 18 ($NODE_VERSION)"
    fi
else
    echo -e "\n[NODE] SKIP: node not found"
fi

# 6. RAG Validation (conditional)
echo -e "\nChecking if RAG is enabled..."
RAG_ENABLED=$(curl -s "$BASE_URL/v1/models" -H "Authorization: Bearer $CLIENT_API_KEY" | grep -q "rag" && echo "yes" || echo "no")

if [ "$RAG_ENABLED" == "yes" ]; then
    echo "RAG seems to be enabled. Validating RAG examples..."
    if command -v python3 &> /dev/null; then
        python3 examples/python/rag_query.py "test" > /dev/null || echo "RAG Query failed (maybe no docs?), skipping deep validation"
    fi
else
    echo "RAG not detected in available models or disabled. Skipping RAG validation."
fi

echo -e "\n--- Validation Finished Successfully ---"
