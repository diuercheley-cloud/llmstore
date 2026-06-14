#!/bin/bash
set -e

# LLM Inference Stack - Release Gate CI
# Source of truth: docs/CI_DECISION.md

TAG=$1
if [ -z "$TAG" ]; then
    echo "Usage: $0 <TAG>"
    exit 1
fi

echo "==> Release Gate CI: Operational Readiness"
make operational-readiness

echo "==> Release Gate CI: Release Gate Validator"
make release-gate TAG=$TAG

echo "==> Release Gate CI: Artifact Verification"
make verify-release-artifacts TAG=$TAG

echo "==> Release Gate CI: Compliance Gate"
make compliance-release-gate TAG=$TAG
