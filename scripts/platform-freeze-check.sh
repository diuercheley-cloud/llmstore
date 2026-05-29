#!/bin/bash
set -e

# Wrapper for python platform freeze check
python3 scripts/platform-freeze-check.py
python3 scripts/check-service-test-coverage.py --gate
