#!/bin/bash
# scripts/validate-landing-local.sh

set -e

URL="${1:-http://localhost:8080}"
FILE="control_plane/app/static/www/index.html"

echo "--------------------------------------------------"
echo "Validating Local Landing Page"
echo "--------------------------------------------------"

if [ ! -f "$FILE" ]; then
    echo "ERROR: File $FILE not found."
    exit 1
fi

echo "[1/3] Checking file content for key sections..."

CHECKS=(
    "LLM Local para Empresas"
    "API compatível com OpenAI"
    "RAG com documentos internos"
    "Controle de clientes, planos e uso"
    "Admin Lab para modelos locais"
    "Operação em localhost ou servidor próprio"
    "Demonstração Local"
    "Client Portal Demo"
    "Admin Dashboard"
    "Developer Docs & Exemplos"
    "Exemplos →"
    "Chatbot com Documentos"
    "Fora do escopo nesta versão"
    "Sem PIX/PSP real nesta versão"
)

for check in "${CHECKS[@]}"; do
    if grep -q "$check" "$FILE"; then
        echo "  [OK] Found: $check"
    else
        echo "  [FAIL] Missing: $check"
        exit 1
    fi
done

echo "[2/3] Checking for forbidden promises (PIX/PSP real active)..."

FORBIDDEN=(
    "PIX real ativo"
    "PSP real ativo"
)

for forbidden in "${FORBIDDEN[@]}"; do
    if grep -q "$forbidden" "$FILE"; then
        echo "  [FAIL] Found forbidden promise: $forbidden"
        exit 1
    else
        echo "  [OK] Not found: $forbidden"
    fi
done

echo "[3/3] Checking local links..."

LINKS=(
    "/portal/"
    "/admin/"
    "/docs"
    "/examples"
    "/getting-started"
)

for link in "${LINKS[@]}"; do
    if grep -q "href=\"$link\"" "$FILE"; then
        echo "  [OK] Link found: $link"
    else
        echo "  [FAIL] Link missing: $link"
        exit 1
    fi
done

echo "--------------------------------------------------"
echo "Landing Page Validation: SUCCESS"
echo "--------------------------------------------------"
