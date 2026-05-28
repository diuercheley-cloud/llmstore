#!/bin/bash
set -e

echo "--- Running Platform Freeze Governance Check ---"
bash scripts/platform-freeze-check.sh
echo "PASS: Freeze governance validated."
