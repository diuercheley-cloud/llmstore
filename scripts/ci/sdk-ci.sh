#!/bin/bash
set -e

# LLM Inference Stack - SDK CI
# Source of truth: docs/CI_DECISION.md

echo "==> SDK CI: Python SDK"
cd sdk/python
pip install -e ".[dev]"
pytest --cov=kleberai
python -m build
twine check dist/*
cd ../..
