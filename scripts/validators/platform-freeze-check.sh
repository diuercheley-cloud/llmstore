#!/bin/bash
set -e

# Wrapper for python platform freeze check
python3 scripts/validators/platform-freeze-check.py
python3 scripts/validators/check-service-test-coverage.py --gate
