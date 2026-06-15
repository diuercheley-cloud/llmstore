#!/bin/bash
set -e

# LLM Inference Stack - Security CI
# Source of truth: docs/CI_DECISION.md

echo "==> Security CI: Secret Scanning"
# Assumption: secrets-check is part of backend-ci or standalone
# We use scripts/validators/check-secrets.sh --all here for redundancy or standalone security job
bash scripts/validators/check-secrets.sh --all

echo "==> Security CI: Dependency Vulnerability Scan (Trivy)"
if command -v trivy &> /dev/null; then
    trivy fs . --severity HIGH,CRITICAL --format sarif --output trivy-results.sarif
else
    echo "Trivy not installed, skipping FS scan."
fi

echo "==> Security CI: Code and Multi-language Security Scan (Bandit & Semgrep)"
pip install bandit semgrep
python3 scripts/validators/validate_security_scan.py

