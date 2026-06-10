#!/bin/bash
set -e

# LLM Inference Stack - Compliance Evidence Collector
# Coleta evidências técnicas sanitizadas para auditorias.

echo "--- Iniciando Coleta de Evidências de Compliance ---"

# 1. Git Metadata
git log -n 50 --pretty=format:"%h %ad %s" > artifacts/compliance/latest/git_history.txt
git tag -l > artifacts/compliance/latest/git_tags.txt

# 2. Project Metadata
cp CHANGELOG.md artifacts/compliance/latest/
cp README.md artifacts/compliance/latest/

# 3. Security & Validation (Latest artifacts)
find artifacts/security-reports -name "*.md" | sort -r | head -n 1 | xargs -I {} cp {} artifacts/compliance/latest/security-latest.md
find artifacts/releases -name "validation.md" | sort -r | head -n 1 | xargs -I {} cp {} artifacts/compliance/latest/validation-latest.md

# 4. CI/CD Logic
cp .github/workflows/ci.yml artifacts/compliance/latest/github-ci.yml
cp .gitlab-ci.yml artifacts/compliance/latest/gitlab-ci.yml

# Sanitização Básica no Script
sed -i 's/PRIVATE KEY/[REDACTED]/gI' artifacts/compliance/latest/* || true
sed -i 's/API_KEY/[REDACTED]/gI' artifacts/compliance/latest/* || true

echo "--- Coleta Finalizada em artifacts/compliance/latest/ ---"
