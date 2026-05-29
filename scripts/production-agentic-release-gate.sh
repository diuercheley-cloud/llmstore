#!/bin/bash
set -e

TAG=$1
if [ -z "$TAG" ]; then
    echo "Erro: Tag de release não fornecida para o production-agentic release gate."
    echo "Uso: scripts/production-agentic-release-gate.sh <TAG>"
    exit 1
fi

# Ensure tag has production keyword
if [[ ! "$TAG" =~ "production" && ! "$TAG" =~ "agentic" && ! "$TAG" =~ "platform" ]]; then
    echo "Erro: A tag '$TAG' deve conter uma das seguintes palavras-chave para o production gate: production, agentic, platform"
    exit 1
fi

echo "Running production-agentic-release-gate with tag $TAG..."
bash scripts/release-gate.sh "$TAG"
