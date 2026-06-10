#!/usr/bin/env bash
set -euo pipefail

# Scripts para expor localmente usando ngrok ou cloudflared (tunnel)
# Requer instalação prévia das ferramentas

PORT=18080

if command -v cloudflared &> /dev/null; then
    echo "--- Expondo llm-inference-stack via Cloudflare Tunnel ---"
    cloudflared tunnel --url "http://localhost:${PORT}"
elif command -v ngrok &> /dev/null; then
    echo "--- Expondo llm-inference-stack via ngrok ---"
    ngrok http "${PORT}"
else
    echo "Erro: cloudflared ou ngrok não encontrados."
    echo "Instale um deles para expor o stack externamente."
    exit 1
fi
