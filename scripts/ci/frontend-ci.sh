#!/bin/bash
set -e

# LLM Inference Stack - Frontend CI
# Source of truth: docs/CI_DECISION.md

echo "==> Frontend CI: Admin Dashboard"
python3 scripts/detect_frontend_mocks.py
cd frontend/admin
npm run lint
npm run build
npm run test
cd ../..

echo "==> Frontend CI: Client Portal"
cd frontend/client
npm run lint
npm run build
cd ../..
