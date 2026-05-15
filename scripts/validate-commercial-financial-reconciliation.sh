#!/bin/bash
set -e

echo "Starting Commercial Financial Reconciliation & Dispute Management validation..."

# 1. Run tests
./.venv/bin/pytest -q \
  tests/test_financial_reconciliation.py \
  tests/test_dispute_management.py \
  tests/test_financial_audit_chain.py

# 2. Check bash scripts for syntax errors
bash -n scripts/validate-commercial-financial-reconciliation.sh

echo "All validations passed successfully!"
