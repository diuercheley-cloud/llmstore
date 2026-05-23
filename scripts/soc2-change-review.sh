#!/bin/bash
set -e

# LLM Inference Stack - SOC 2 Change Review
# Consolida evidências de mudanças para revisão de release.

echo "--- Gerando Relatório de Revisão de Mudanças ---"

# 1. Commits entre releases
git log -n 20 --pretty=format:"%h - %s (%an)" > artifacts/compliance/latest/change-review-data.txt

# 2. Release Gate Results
find artifacts/releases -name "validation.md" | head -n 1 | xargs cat >> artifacts/compliance/latest/change-review-data.txt

echo "Dados consolidados em artifacts/compliance/latest/change-review-data.txt"
