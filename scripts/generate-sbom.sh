#!/bin/bash
set -e

# LLM Inference Stack - SBOM Generator
# Gera a lista de materiais de software para garantir rastreabilidade.

TAG=$1
if [ -z "$TAG" ]; then
    TAG=$(cat VERSION 2>/dev/null || echo "v0.0.0")
fi

ARTIFACT_DIR="artifacts/releases/$TAG"
mkdir -p "$ARTIFACT_DIR"

echo "--- Gerando SBOM para $TAG ---"

# 1. Python SBOM (Simple requirements list)
echo "Gerando Python SBOM..."
pip freeze > "$ARTIFACT_DIR/python-sbom.txt"

# 2. Node SBOM
echo "Gerando Node SBOM..."
if [ -d "frontend/admin" ]; then
    cd frontend/admin
    npm list --all --json > "../../$ARTIFACT_DIR/node-sbom.json"
    cd ../..
fi

# 3. Docker SBOM (If tool is available)
if command -v docker &> /dev/null && command -v docker sbom &> /dev/null; then
    echo "Gerando Docker SBOM..."
    # docker sbom llm-inference-stack/control-plane:latest --output "$ARTIFACT_DIR/docker-sbom.json"
fi

echo "SBOMs gerados em $ARTIFACT_DIR"
